import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.metrics import confusion_matrix

RANDOM_STATE = 42
N_FEATURES = 57

FEATURE_NAMES = []

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR.parent / "artifacts"


def export_tree(estimator):
    t = estimator.tree_
    return {
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": t.threshold.tolist(),
        "value": t.value.squeeze(axis=1).tolist(),  # [n_nodes][n_classes]
    }


def export_forest(model):
    return {
        "model_type": "RandomForestClassifier",
        "n_classes": int(model.n_classes_),
        "n_features_in": int(model.n_features_in_),
        "classes": model.classes_.tolist(),
        "trees": [export_tree(est) for est in model.estimators_],
    }

def feature_engineering(train_df, test_df):
    # drop irrelevant rows
    del_cols = ['Unnamed: 0']
    train_df = train_df.drop(columns=del_cols)
    del_cols = ['Unnamed: 0']
    test_df = test_df.drop(columns=del_cols)

    # distance from merchant
    user_lat = np.radians(train_df['lat'])
    user_long = np.radians(train_df['long'])
    merch_lat = np.radians(train_df['merch_lat'])
    merch_long = np.radians(train_df['merch_long'])

    dlat = merch_lat - user_lat
    dlong = merch_long - user_long

    a = np.sin(dlat/2)**2 + np.cos(user_lat) * np.cos(merch_lat) * np.sin(dlong/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    train_df["merch_dist"] = 6371 * c * 0.621371
    # ---------------------------------------------
    user_lat = np.radians(test_df['lat'])
    user_long = np.radians(test_df['long'])
    merch_lat = np.radians(test_df['merch_lat'])
    merch_long = np.radians(test_df['merch_long'])

    dlat = merch_lat - user_lat
    dlong = merch_long - user_long

    a = np.sin(dlat/2)**2 + np.cos(user_lat) * np.cos(merch_lat) * np.sin(dlong/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    test_df["merch_dist"] = 6371 * c * 0.621371
    print("     Distance from merchant feature processed.")


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

    # transaction time details
    train_df['trans_date_time_global'] = pd.to_datetime(train_df["trans_date_trans_time"])
    train_df['trans_date_global'] = train_df['trans_date_time_global'].dt.date
    train_df['trans_date_time_local'] = train_df['trans_date_time_global'] + pd.to_timedelta(train_df['state'].map(state_offset), unit='h')
    train_df['trans_date_local'] = train_df['trans_date_time_local'].dt.date
    train_df['weekday'] = train_df['trans_date_time_local'].dt.weekday
    train_df['time_hrs'] = train_df['trans_date_time_local'].dt.hour + train_df['trans_date_time_local'].dt.minute/60 + train_df['trans_date_time_local'].dt.second/3600
    # ------------------------------------------
    test_df['trans_date_time_global'] = pd.to_datetime(test_df["trans_date_trans_time"])
    test_df['trans_date_global'] = test_df['trans_date_time_global'].dt.date
    test_df['trans_date_time_local'] = test_df['trans_date_time_global'] + pd.to_timedelta(test_df['state'].map(state_offset), unit='h')
    test_df['trans_date_local'] = test_df['trans_date_time_local'].dt.date
    test_df['weekday'] = test_df['trans_date_time_local'].dt.weekday
    test_df['time_hrs'] = test_df['trans_date_time_local'].dt.hour + test_df['trans_date_time_local'].dt.minute/60 + test_df['trans_date_time_local'].dt.second/3600
    print("     Transaction time features processed.")


    # time and distance from last transaction
    train_df = train_df.sort_values(["cc_num", "trans_date_time_global"])
    train_df['time_since_last'] = train_df.groupby('cc_num')['trans_date_time_global'].diff().dt.total_seconds() / 3600

    merch_lat = np.radians(train_df['merch_lat'])
    merch_long = np.radians(train_df['merch_long'])
    prev_merch_lat = np.radians(train_df.groupby('cc_num')['merch_lat'].shift(1))
    prev_merch_long = np.radians(train_df.groupby('cc_num')['merch_long'].shift(1))

    dlat = merch_lat - prev_merch_lat
    dlong = merch_long - prev_merch_long

    a = np.sin(dlat/2)**2 + np.cos(merch_lat) * np.cos(prev_merch_lat) * np.sin(dlong/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    train_df['dist_from_last'] = 6371 * c * 0.621371
    # ---------------------------------------------------
    test_df = test_df.sort_values(["cc_num", "trans_date_time_global"])
    test_df['time_since_last'] = test_df.groupby('cc_num')['trans_date_time_global'].diff().dt.total_seconds() / 3600

    merch_lat = np.radians(test_df['merch_lat'])
    merch_long = np.radians(test_df['merch_long'])
    prev_merch_lat = np.radians(test_df.groupby('cc_num')['merch_lat'].shift(1))
    prev_merch_long = np.radians(test_df.groupby('cc_num')['merch_long'].shift(1))

    dlat = merch_lat - prev_merch_lat
    dlong = merch_long - prev_merch_long

    a = np.sin(dlat/2)**2 + np.cos(merch_lat) * np.cos(prev_merch_lat) * np.sin(dlong/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    test_df['dist_from_last'] = 6371 * c * 0.621371
    print("     Time/Distance from last transaction features processed.")

    # age
    train_df['age'] = (pd.Timestamp('today') - pd.to_datetime(train_df["dob"])).dt.days / 365.25
    # --------------------------------------------
    test_df['age'] = (pd.Timestamp('today') - pd.to_datetime(test_df["dob"])).dt.days / 365.25
    print("     Age feature processed.")


    # daily spending stats
    train_df['cum_sum_amt'] = train_df.groupby('cc_num')['amt'].cumsum() - train_df['amt']
    train_df['cum_count_amt'] = train_df.groupby('cc_num')['amt'].cumcount()

    train_df['avg_amt'] = train_df['cum_sum_amt'] / train_df['cum_count_amt']
    train_df['median_amt'] = train_df.groupby('cc_num')['amt'].apply(lambda x: x.expanding().median().shift()).reset_index(level=0, drop=True)
    train_df['max_spent'] = train_df.groupby('cc_num')['amt'].cummax().shift()

    train_df['daily_total'] = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].cumsum() - train_df['amt']
    train_df['daily_count'] = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].cumcount()

    avg_daily_spending = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].sum().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    train_df['avg_daily_spending'] = train_df.set_index(['cc_num', 'trans_date_local']).index.map(avg_daily_spending)
    max_spent_day = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].sum().groupby('cc_num').cummax().shift()
    train_df['max_spent_day'] = train_df.set_index(['cc_num', 'trans_date_local']).index.map(max_spent_day)
    avg_daily_count = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].count().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    train_df['avg_daily_count'] = train_df.set_index(['cc_num', 'trans_date_local']).index.map(avg_daily_count)
    max_daily_count = train_df.groupby(['cc_num', 'trans_date_local'])['amt'].count().groupby('cc_num').expanding().max().shift().reset_index(level=0, drop=True)
    train_df['max_daily_count'] = train_df.set_index(['cc_num', 'trans_date_local']).index.map(max_daily_count)

    train_df['amt_vs_avg_amt'] = train_df['amt'] / train_df['avg_amt']
    train_df['amt_vs_avg_daily'] = train_df['amt'] / train_df['avg_daily_spending']
    train_df['amt_vs_max_spent'] = train_df['amt'] / train_df['max_spent']
    train_df['amt_vs_max_spent_day'] = train_df['amt'] / train_df['max_spent_day']

    train_df['daily_total_vs_avg_daily_spending'] = train_df['daily_total'] / train_df['avg_daily_spending']

    train_df['daily_count_vs_avg_daily_count'] = train_df['daily_count'] / train_df['avg_daily_count']
    train_df['daily_count_vs_max_daily_count'] = train_df['daily_count'] / train_df['max_daily_count']
    # ---------------------------------------------------
    test_df['cum_sum_amt'] = test_df.groupby('cc_num')['amt'].cumsum() - test_df['amt']
    test_df['cum_count_amt'] = test_df.groupby('cc_num')['amt'].cumcount()

    test_df['avg_amt'] = test_df['cum_sum_amt'] / test_df['cum_count_amt']
    test_df['median_amt'] = test_df.groupby('cc_num')['amt'].apply(lambda x: x.expanding().median().shift()).reset_index(level=0, drop=True)
    test_df['max_spent'] = test_df.groupby('cc_num')['amt'].cummax().shift()

    test_df['daily_total'] = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].cumsum() - test_df['amt']
    test_df['daily_count'] = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].cumcount()

    avg_daily_spending = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].sum().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    test_df['avg_daily_spending'] = test_df.set_index(['cc_num', 'trans_date_local']).index.map(avg_daily_spending)
    max_spent_day = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].sum().groupby('cc_num').cummax().shift()
    test_df['max_spent_day'] = test_df.set_index(['cc_num', 'trans_date_local']).index.map(max_spent_day)
    avg_daily_count = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].count().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    test_df['avg_daily_count'] = test_df.set_index(['cc_num', 'trans_date_local']).index.map(avg_daily_count)
    max_daily_count = test_df.groupby(['cc_num', 'trans_date_local'])['amt'].count().groupby('cc_num').expanding().max().shift().reset_index(level=0, drop=True)
    test_df['max_daily_count'] = test_df.set_index(['cc_num', 'trans_date_local']).index.map(max_daily_count)

    test_df['amt_vs_avg_amt'] = test_df['amt'] / test_df['avg_amt']
    test_df['amt_vs_avg_daily'] = test_df['amt'] / test_df['avg_daily_spending']
    test_df['amt_vs_max_spent'] = test_df['amt'] / test_df['max_spent']
    test_df['amt_vs_max_spent_day'] = test_df['amt'] / test_df['max_spent_day']

    test_df['daily_total_vs_avg_daily_spending'] = test_df['daily_total'] / test_df['avg_daily_spending']

    test_df['daily_count_vs_avg_daily_count'] = test_df['daily_count'] / test_df['avg_daily_count']
    test_df['daily_count_vs_max_daily_count'] = test_df['daily_count'] / test_df['max_daily_count']
    print("     Daily spending stats features processed.")


    # weekly/monthly stats
    train_df['year'] = train_df['trans_date_time_local'].dt.isocalendar().year
    train_df['week'] = train_df['trans_date_time_local'].dt.isocalendar().week

    train_df['weekly_total'] = train_df.groupby(['cc_num', 'year', 'week'])['amt'].cumsum() - train_df['amt']
    train_df['weekly_count'] = train_df.groupby(['cc_num', 'year', 'week'])['amt'].cumcount()

    avg_weekly_spending = train_df.groupby(['cc_num', 'year', 'week'])['amt'].sum().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    train_df['avg_weekly_spending'] = train_df.set_index(['cc_num', 'year', 'week']).index.map(avg_weekly_spending)
    avg_weekly_count = train_df.groupby(['cc_num', 'year', 'week'])['amt'].count().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    train_df['avg_weekly_count'] = train_df.set_index(['cc_num', 'year', 'week']).index.map(avg_weekly_count)

    train_df['amt_vs_avg_weekly'] = train_df['amt'] / train_df['avg_weekly_spending']
    train_df['weekly_count_vs_avg_weekly_count'] = train_df['weekly_count'] / train_df['avg_weekly_count']

    train_df['daily_total_vs_avg_weekly_spending'] = train_df['daily_total'] / train_df['avg_weekly_spending']
    # ----------------------------------------------------
    test_df['year'] = test_df['trans_date_time_local'].dt.isocalendar().year
    test_df['week'] = test_df['trans_date_time_local'].dt.isocalendar().week

    test_df['weekly_total'] = test_df.groupby(['cc_num', 'year', 'week'])['amt'].cumsum() - test_df['amt']
    test_df['weekly_count'] = test_df.groupby(['cc_num', 'year', 'week'])['amt'].cumcount()

    avg_weekly_spending = test_df.groupby(['cc_num', 'year', 'week'])['amt'].sum().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    test_df['avg_weekly_spending'] = test_df.set_index(['cc_num', 'year', 'week']).index.map(avg_weekly_spending)
    avg_weekly_count = test_df.groupby(['cc_num', 'year', 'week'])['amt'].count().groupby('cc_num').expanding().mean().shift().reset_index(level=0, drop=True)
    test_df['avg_weekly_count'] = test_df.set_index(['cc_num', 'year', 'week']).index.map(avg_weekly_count)

    test_df['amt_vs_avg_weekly'] = test_df['amt'] / test_df['avg_weekly_spending']
    test_df['weekly_count_vs_avg_weekly_count'] = test_df['weekly_count'] / test_df['avg_weekly_count']

    test_df['daily_total_vs_avg_weekly_spending'] = test_df['daily_total'] / test_df['avg_weekly_spending']
    print("     Weekly spending stats features processed.")


    # merchant/category stats
    train_df['merchant_count'] = train_df.groupby(['cc_num', 'merchant']).cumcount()
    train_df['merchant_trans_ratio'] = train_df['merchant_count'] / train_df.groupby(['cc_num']).cumcount()
    merchant_amt = train_df.groupby(['cc_num', 'merchant'])['amt'].cumsum() - train_df['amt']
    train_df['merchant_avg_amt'] = merchant_amt / train_df['merchant_count']
    train_df['amt_vs_merchant_avg_amt'] = train_df['amt'] / train_df['merchant_avg_amt']

    train_df['cat_count'] = train_df.groupby(['cc_num', 'category']).cumcount()
    train_df['cat_trans_ratio'] = train_df['cat_count'] / train_df.groupby(['cc_num']).cumcount()
    cat_amt = train_df.groupby(['cc_num', 'category'])['amt'].cumsum() - train_df['amt']
    train_df['cat_avg_amt'] = cat_amt / train_df['cat_count']
    train_df['amt_vs_cat_avg_amt'] = train_df['amt'] / train_df['cat_avg_amt']
    # -------------------------------------------------
    test_df['merchant_count'] = test_df.groupby(['cc_num', 'merchant']).cumcount()
    test_df['merchant_trans_ratio'] = test_df['merchant_count'] / test_df.groupby(['cc_num']).cumcount()
    merchant_amt = test_df.groupby(['cc_num', 'merchant'])['amt'].cumsum() - test_df['amt']
    test_df['merchant_avg_amt'] = merchant_amt / test_df['merchant_count']
    test_df['amt_vs_merchant_avg_amt'] = test_df['amt'] / test_df['merchant_avg_amt']

    test_df['cat_count'] = test_df.groupby(['cc_num', 'category']).cumcount()
    test_df['cat_trans_ratio'] = test_df['cat_count'] / test_df.groupby(['cc_num']).cumcount()
    cat_amt = test_df.groupby(['cc_num', 'category'])['amt'].cumsum() - test_df['amt']
    test_df['cat_avg_amt'] = cat_amt / test_df['cat_count']
    test_df['amt_vs_cat_avg_amt'] = test_df['amt'] / test_df['cat_avg_amt']
    print("     Merchant and category stats features processed.")


    # TODO: export current training and testing datasets with columns into dynamodb
    # these will later be pulled into dynamoDB to do feature engineering for incoming transactions?
    # or will pull from new transactions for feature engineering

    # data cleaning
    train_df.fillna(-1, inplace=True)
    test_df.fillna(-1, inplace=True)

    # drop irrelevant rows for model 
    del_cols = ['trans_date_trans_time', 'cc_num', 'merchant', 'city', 'state', 'dob', 'unix_time', 
                'trans_date_time_global', 'trans_date_global', 'trans_date_time_local', 'trans_date_local',
                'year', 'week', 'cum_sum_amt', 'cum_count_amt',  'first', 'last', 'gender', 'street', 
                'zip', 'job', 'trans_num']
    train_df = train_df.drop(columns=del_cols)
    test_df = test_df.drop(columns=del_cols)
    print("     Data cleaning and feature selection completed.")


    # one-hot encode categorical features
    train_df = pd.get_dummies(train_df, columns=["category"], prefix="cat")
    test_df = pd.get_dummies(test_df, columns=["category"], prefix="cat")
    print("     One hot encoding for category feature processed.")

    return train_df, test_df

def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # training/testing/evaluating model
    print("Uploading data...")
    train_df = pd.read_csv("../datasets/fraudTrain.csv")
    test_df = pd.read_csv("../datasets/fraudTest.csv")

    print("Initiating feature engineering...")
    train_df, test_df = feature_engineering(train_df, test_df)

    X_train = train_df.drop(columns=['is_fraud'])
    Y_train = train_df['is_fraud']

    X_test = test_df.drop(columns=['is_fraud'])
    Y_test = test_df['is_fraud']

    FEATURE_NAMES = list(X_train.columns)
    N_FEATURES = len(FEATURE_NAMES)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_STATE
    )

    print("Training model...")
    model.fit(X_train, Y_train)

    print("Testing model...")
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)

    print("Evaluating model...")
    auc = roc_auc_score(Y_test, test_probs)
    print(f"Test ROC AUC: {auc:.4f}")
    print(classification_report(Y_test, test_preds))
    print("Confusion Matrix:\n[[TN, FP],\n[FN, TP]]\n", confusion_matrix(Y_test, test_preds))

    print("Creating CDF...")

    X = pd.concat([X_train, X_test])
    all_probs = model.predict_proba(X)[:, 1]
    sorted_probs = np.sort(all_probs)
    cdf_values = (np.arange(1, len(sorted_probs) + 1) / len(sorted_probs)).tolist()

    # packaging and exporting model
    print("Packaging and exporting model components...")
    forest_path = ARTIFACT_DIR / "fraud_forest.json"
    cdf_path = ARTIFACT_DIR / "fraud_cdf.json"
    meta_path = ARTIFACT_DIR / "feature_metadata.json"

    forest_path.write_text(json.dumps(export_forest(model)))
    cdf_path.write_text(json.dumps({
        "sorted_probs": sorted_probs.tolist(),
        "cdf_values": cdf_values,
    }))
    meta_path.write_text(json.dumps({
        "feature_names": FEATURE_NAMES,
        "model_type": "RandomForestClassifier",
        "notes": "Pure-Python exported forest for Lambda scoring demo",
    }, indent=2))

    print(f"Saved forest to {forest_path}")
    print(f"Saved CDF to   {cdf_path}")
    print(f"Saved meta to  {meta_path}")


if __name__ == "__main__":
    main()