import json
from bisect import bisect_left
from pathlib import Path
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import numpy as np
import statistics
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts" # maybe add .parent after BASE_DIR if issues

MODEL_PATH = ARTIFACT_DIR / "fraud_forest.json"
CDF_PATH = ARTIFACT_DIR / "fraud_cdf.json"
META_PATH = ARTIFACT_DIR / "feature_metadata.json"

forest = json.loads(MODEL_PATH.read_text())
cdf_data = json.loads(CDF_PATH.read_text())
metadata = json.loads(META_PATH.read_text())

FEATURE_NAMES = metadata["feature_names"]
sorted_probs = cdf_data["sorted_probs"]
cdf_values = cdf_data["cdf_values"]

def get_prior_transactions(card_number, current_timestamp):
    dynamodb = boto3.resource("dynamodb")
    TRANSACTIONS_TABLE = dynamodb.Table("transactions")

    items = []
    response = TRANSACTIONS_TABLE.query(
        KeyConditionExpression=
            Key("cardNumber").eq(card_number) & Key("transactionTimestamp").lt(current_timestamp),
        ScanIndexForward=False
    )
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = TRANSACTIONS_TABLE.query(
            KeyConditionExpression=
                Key("cardNumber").eq(card_number) & Key("transactionTimestamp").lt(current_timestamp),
            ScanIndexForward=False,
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))
    return items

def normalize_transaction(txn):
    FIELD_MAP = {
        "cardNumber": "cc_num",
        "transactionTimestamp": "trans_date_trans_time",
        "amount": "amt",
        "category": "category",
        "city": "city",
        "cityPopulation": "city_pop",
        "customerLatitude": "lat",
        "customerLongitude": "long",
        "dateOfBirth": "dob",
        "firstName": "first",
        "gender": "gender",
        "job": "job",
        "lastName": "last",
        "merchant": "merchant",
        "merchantLatitude": "merch_lat",
        "merchantLongitude": "merch_long",
        "state": "state",
        "street": "street",
        "unixTime": "unix_time",
        "zipCode": "zip",
    }

    numeric_fields = {
        "amt", "lat", "long", "merch_lat", "merch_long", "city_pop", "unix_time", "cc_num", "zip"
    }

    normalized = {}
    for raw_key, new_key in FIELD_MAP.items():
        if raw_key in txn:
            val = txn[raw_key]

            if isinstance(val, Decimal) and new_key in numeric_fields:
                val = float(val) # convert Decimal from dynamoDB to float to avoid weird bugs

            normalized[new_key] = val
    return normalized

def parse_timestamp(txn):
     # state offsets used for calculating local time of transactions
    state_offset = {
        # Eastern
        'ME': -5, 'NH': -5, 'VT': -5, 'MA': -5, 'RI': -5, 'CT': -5, 'NY': -5, 'NJ': -5,
        'PA': -5, 'DE': -5, 'MD': -5, 'DC': -5, 'WV': -5, 'OH': -5, 'MI': -5, 'GA': -5,
        'FL': -5, 'SC': -5, 'NC': -5, 'VA': -5, 'KY': -5, 'IN': -5,
        # Central
        'AL': -6, 'AR': -6, 'IL': -6, 'IA': -6, 'KS': -6, 'LA': -6, 'MN': -6, 'MS': -6,
        'MO': -6, 'NE': -6, 'ND': -6, 'OK': -6, 'SD': -6, 'TX': -6, 'WI': -6, 'TN': -6,
        # Mountain
        'AZ': -7, 'CO': -7, 'ID': -7, 'MT': -7, 'NM': -7, 'UT': -7, 'WY': -7,
        # Pacific
        'CA': -8, 'NV': -8, 'OR': -8, 'WA': -8,
        # Alaska
        'AK': -9,
        # Hawaii
        'HI': -10
    }

    time_stamp = txn["trans_date_trans_time"]
    if time_stamp.endswith("Z"):
        time_stamp = time_stamp[:-1] + "+00:00"
    txn["trans_date_time_global"] = datetime.fromisoformat(time_stamp)
    txn["trans_date_global"] = txn['trans_date_time_global'].date()

    offset_hours = state_offset.get(txn['state'], 0)
    txn['trans_date_time_local'] = (txn['trans_date_time_global'] + timedelta(hours=offset_hours))
    txn['trans_date_local'] = txn['trans_date_time_local'].date()

    txn['weekday'] = txn['trans_date_time_local'].weekday()
    txn['time_hrs'] = (
        txn["trans_date_time_local"].hour + 
        txn["trans_date_time_local"].minute / 60 + 
        txn["trans_date_time_local"].second / 3600
    )

    txn['year'] = txn['trans_date_time_local'].isocalendar().year
    txn['week'] = txn['trans_date_time_local'].isocalendar().week

    return txn

def compute_features(transaction, prior_transactions):
    # get the right column mapping names for engineering
    current_txn = normalize_transaction(transaction)
    prior_txns = [
        normalize_transaction(prior_txn) for prior_txn in prior_transactions
    ]

    # distance from merchant
    user_lat = np.radians(current_txn['lat'])
    user_long = np.radians(current_txn['long'])
    merch_lat = np.radians(current_txn['merch_lat'])
    merch_long = np.radians(current_txn['merch_long'])
 
    dlat = merch_lat - user_lat
    dlong = merch_long - user_long

    a = np.sin(dlat/2)**2 + np.cos(user_lat) * np.cos(merch_lat) * np.sin(dlong/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    current_txn["merch_dist"] = 6371 * c * 0.621371

    # get additional time details for feature engineering
    current_txn = parse_timestamp(current_txn)
    prior_txns = [parse_timestamp(txn) for txn in prior_txns]

    # time and distance from last transaction
    current_txn['time_since_last'] = (
        (current_txn['trans_date_time_global'] - prior_txns[0]['trans_date_time_global']).total_seconds() / 3600
        if prior_txns else -1
    )

    if prior_txns:
        merch_lat = np.radians(current_txn['merch_lat'])
        merch_long = np.radians(current_txn['merch_long'])
        prev_merch_lat = np.radians(prior_txns[0]['merch_lat'])
        prev_merch_long = np.radians(prior_txns[0]['merch_long'])

        dlat = merch_lat - prev_merch_lat
        dlong = merch_long - prev_merch_long

        a = np.sin(dlat/2)**2 + np.cos(merch_lat) * np.cos(prev_merch_lat) * np.sin(dlong/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        current_txn['dist_from_last'] = 6371 * c * 0.621371
    else: 
        current_txn['dist_from_last'] = -1

    # age
    current_txn['age'] =  (datetime.now() - datetime.fromisoformat(current_txn['dob'])).days / 365.25

    # daily spending stats
    amts = []
    cum_sum_amt = 0
    cum_count_amt = 0
    for txn in prior_txns:
        curr_amt = txn['amt']
        amts.append(curr_amt)
        cum_sum_amt += curr_amt
        cum_count_amt += 1
    
    current_txn["avg_amt"] = cum_sum_amt / cum_count_amt if amts else -1
    current_txn["median_amt"] = statistics.median(amts) if amts else -1
    current_txn["max_spent"] = max(amts) if amts else -1
    
    daily_total = 0
    daily_count = 0
    daily_totals = []
    daily_counts = []
    day_tracker = None
    day_index = -1
    for txn in prior_txns:
        curr_day = txn["trans_date_local"]
        # day of incoming transaction so get those stats
        if (curr_day == current_txn["trans_date_local"]):
            daily_total += txn['amt']
            daily_count += 1
        else:         # different day so get those stats for our daily stats
            if (day_index == -1): 
                day_tracker = curr_day
                day_index = 0
                daily_totals.append(0)
                daily_counts.append(0)
            elif (curr_day != day_tracker): # counting on a different day -> we need to update where we are aggregating
                day_index += 1
                day_tracker = curr_day
                daily_totals.append(0)
                daily_counts.append(0)
            daily_totals[day_index] += txn['amt']
            daily_counts[day_index] += 1

    current_txn['daily_total'] = daily_total
    current_txn['daily_count'] = daily_count

    current_txn['avg_daily_spending'] = sum(daily_totals) / len(daily_totals) if daily_totals else -1
    current_txn["max_spent_day"] = max(daily_totals) if daily_totals else -1
    current_txn["avg_daily_count"] = sum(daily_counts) / len(daily_counts) if daily_counts else -1
    current_txn["max_daily_count"] = max(daily_counts) if daily_counts else -1

    current_txn['amt_vs_avg_amt'] = (
        current_txn['amt'] / current_txn['avg_amt']
        if current_txn['avg_amt'] not in (0, -1) else -1
    )
    current_txn['amt_vs_avg_daily'] = (
        current_txn['amt'] / current_txn['avg_daily_spending'] 
        if current_txn['avg_daily_spending'] not in (0, -1) else -1
    )
    current_txn['amt_vs_max_spent'] = (
        current_txn['amt'] / current_txn['max_spent']
        if current_txn['max_spent'] not in (0, -1) else -1
    )
    current_txn['amt_vs_max_spent_day'] = (
        current_txn['amt'] / current_txn['max_spent_day']
        if current_txn['max_spent_day'] not in (0, -1) else -1
    )
    current_txn['daily_total_vs_avg_daily_spending'] = (
        current_txn['daily_total'] / current_txn['avg_daily_spending']
        if current_txn['avg_daily_spending'] not in (0, -1) else -1
    )
    current_txn['daily_count_vs_avg_daily_count'] = (
        current_txn['daily_count'] / current_txn['avg_daily_count']
        if current_txn['avg_daily_count'] not in (0, -1) else -1
    )
    current_txn['daily_count_vs_max_daily_count'] = (
        current_txn['daily_count'] / current_txn['max_daily_count']
        if current_txn['max_daily_count'] not in (0, -1) else -1
    )
    # weekly stats
    weekly_total = 0
    weekly_count = 0
    weekly_totals = []
    weekly_counts = []
    week_tracker = None
    year_tracker = None
    week_index = -1
    for txn in prior_txns:
        curr_week = txn["week"]
        curr_year = txn["year"]
        # week of incoming transaction so get those stats
        if (curr_week == current_txn["week"] and curr_year == current_txn["year"]):
            weekly_total += txn['amt']
            weekly_count += 1
        else:         # different week so get those stats for our weekly stats
            if (week_index == -1): 
                week_tracker = curr_week
                year_tracker = curr_year
                week_index = 0
                weekly_totals.append(0)
                weekly_counts.append(0)
            elif (curr_week != week_tracker or curr_year != year_tracker): # counting on a different week -> we need to update where we are aggregating
                week_index += 1
                week_tracker = curr_week
                year_tracker = curr_year
                weekly_totals.append(0)
                weekly_counts.append(0)
            weekly_totals[week_index] += txn['amt']
            weekly_counts[week_index] += 1

    current_txn['weekly_total'] = weekly_total
    current_txn['weekly_count'] = weekly_count

    current_txn['avg_weekly_spending'] = sum(weekly_totals) / len(weekly_totals) if weekly_totals else -1
    current_txn['avg_weekly_count'] = sum(weekly_counts) / len(weekly_counts) if weekly_counts else -1

    current_txn['amt_vs_avg_weekly'] = (
        current_txn['amt'] / current_txn['avg_weekly_spending']
        if current_txn['avg_weekly_spending'] not in (0, -1) else -1
    )
    current_txn['weekly_count_vs_avg_weekly_count'] = (
        current_txn['weekly_count'] / current_txn['avg_weekly_count']
        if current_txn['avg_weekly_count'] not in (0, -1) else -1
    )
    current_txn['daily_total_vs_avg_weekly_spending'] = (
        current_txn['daily_total'] / current_txn['avg_weekly_spending']
        if current_txn['avg_weekly_spending'] not in (0, -1) else -1
    )
    # merchant/category stats
    merchant_count = 0
    merchant_amt = 0
    category_count = 0
    category_amt = 0
    for txn in prior_txns:
        if (txn['merchant'] == current_txn['merchant']):
            merchant_count += 1
            merchant_amt += txn['amt']
        if (txn['category'] == current_txn['category']):
            category_count += 1
            category_amt += txn['amt']

    current_txn['merchant_count'] = merchant_count
    current_txn['merchant_avg_amt'] = merchant_amt / merchant_count if merchant_count > 0 else -1
    current_txn['amt_vs_merchant_avg_amt'] = (
        current_txn['amt'] / current_txn['merchant_avg_amt'] 
        if current_txn['merchant_avg_amt'] not in (0, -1) else -1
    )
    current_txn['merchant_trans_ratio'] = current_txn['merchant_count'] / cum_count_amt if cum_count_amt > 0 else -1

    current_txn['cat_count'] = category_count
    current_txn['cat_avg_amt'] = category_amt / category_count if category_count > 0 else -1
    current_txn['amt_vs_cat_avg_amt'] = (
        current_txn['amt'] / current_txn['cat_avg_amt'] 
        if current_txn['cat_avg_amt'] not in (0, -1) else -1
    )
    current_txn['cat_trans_ratio'] = current_txn['cat_count'] / cum_count_amt if cum_count_amt > 0 else -1

    # one-hot encoding of category
    CATEGORY_COLUMNS = [
        "cat_entertainment",
        "cat_food_dining",
        "cat_gas_transport",
        "cat_grocery_net",
        "cat_grocery_pos",
        "cat_health_fitness",
        "cat_home",
        "cat_kids_pets",
        "cat_misc_net",
        "cat_misc_pos",
        "cat_personal_care",
        "cat_shopping_net",
        "cat_shopping_pos",
        "cat_travel"
    ]

    category = current_txn['category']
    for col in CATEGORY_COLUMNS:
        cat_name = col.replace("cat_", "")
        current_txn[col] = 1 if category == cat_name else 0

    return current_txn

def build_feature_vector(transaction: dict):
    card_number = transaction["cardNumber"]
    current_timestamp = transaction["transactionTimestamp"]
    prior_transactions = get_prior_transactions(card_number, current_timestamp)

    transaction = compute_features(transaction, prior_transactions)

    values = []
    for name in FEATURE_NAMES:
        if name not in transaction:
            raise ValueError(f"Missing required feature: {name}")
        values.append(float(transaction[name]))
    return values


def predict_tree_probability(tree, features):
    node = 0
    children_left = tree["children_left"]
    children_right = tree["children_right"]
    feature = tree["feature"]
    threshold = tree["threshold"]
    value = tree["value"]

    while children_left[node] != children_right[node]:
        feat_idx = feature[node]
        if features[feat_idx] <= threshold[node]:
            node = children_left[node]
        else:
            node = children_right[node]

    counts = value[node]
    total = sum(counts)
    if total == 0:
        return 0.0
    return counts[1] / total


def predict_probability(features):
    probs = [predict_tree_probability(tree, features) for tree in forest["trees"]]
    return sum(probs) / len(probs)


def score_probability_to_percentile(prob: float) -> float:
    idx = bisect_left(sorted_probs, prob)
    if idx <= 0:
        return float(cdf_values[0])
    if idx >= len(sorted_probs):
        return float(cdf_values[-1])

    x0, x1 = sorted_probs[idx - 1], sorted_probs[idx]
    y0, y1 = cdf_values[idx - 1], cdf_values[idx]

    if x1 == x0:
        return float(y1)

    frac = (prob - x0) / (x1 - x0)
    return float(y0 + frac * (y1 - y0))


def parse_event(event: dict) -> dict:
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return event


def lambda_handler(event, context):
    try:
        payload = parse_event(event)
        transaction = payload["transaction"] if "transaction" in payload else payload

        features = build_feature_vector(transaction)
        pred_prob = float(predict_probability(features))
        fraud_score = score_probability_to_percentile(pred_prob)

        response = {
            "prediction_probability": pred_prob,
            "fraud_score": fraud_score,
            "feature_order": FEATURE_NAMES,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }