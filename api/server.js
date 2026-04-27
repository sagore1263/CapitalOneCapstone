import express from "express";
import crypto from "crypto";

const app = express();
app.use(express.json());



const txById = new Map();                
const txIdsByUserId = new Map();         
const externalIdByUserId = new Map();   
const usersById = new Map();
const userIdByPhone = new Map();


//POST structure
/**
 * User shape from spec:
 * id (server-generated)
 * phone_num (unique)
 * email (optional)
 * threshold (0..1, default 0.5)
 * created_at (timestamp)
 */


//validators for phone email and threshold with regex
function isValidPhoneE164(phone) {
  return typeof phone === "string" && /^\+[1-9]\d{7,14}$/.test(phone);
}
function isValidEmail(email) {
  return typeof email === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
function isValidThreshold(t) {
  return typeof t === "number" && Number.isFinite(t) && t >= 0 && t <= 1;
}

//Endpoint 1: Create account 
//POST /api/v1/users 
app.post("/api/v1/users", (req, res) => {
  const { phone_num, email, threshold } = req.body ?? {};

  //invalid number returns 400
  if (!isValidPhoneE164(phone_num)) {
    return res.status(400).json({
      error: "Invalid phone_num. Expected E.164 like +16085551234",
    });
  }

  //invalid email returns 400
  if (email !== undefined && !isValidEmail(email)) {
    return res.status(400).json({ error: "Invalid email format" });
  }

  //default threshold: 0.5 for now, can change later  
  const finalThreshold = threshold === undefined ? 0.5 : threshold;

  //invalid threshold returns 400
  if (!isValidThreshold(finalThreshold)) {
    return res.status(400).json({ error: "threshold must be a number between 0 and 1" });
  }

  //uniqueness on phone_num, duplicates return 409 Conflict
  if (userIdByPhone.has(phone_num)) {
    return res.status(409).json({ error: "phone_num already exists" });
  }

  const id = crypto.randomUUID(); //generate random uid strings for now, can change to simpler numbers later
  const created_at = new Date().toISOString();

  const user = {
    id,
    phone_num,
    email: email ?? null,
    threshold: finalThreshold,
    created_at,
  };

  usersById.set(id, user);
  userIdByPhone.set(phone_num, id);

  return res.status(200).json(user);
});


// Endpoint 2: List all users
// GET /api/v1/users
app.get("/api/v1/users", (req, res) => {
  const users = Array.from(usersById.values());

  return res.status(200).json({
    count: users.length,
    users,
  });
});


// Endpoint 3: Get a user by ID
// GET /api/v1/users/:userId
app.get("/api/v1/users/:userId", (req, res) => {
  const { userId } = req.params;
  const user = usersById.get(userId);

  if (!user) {
    return res.status(404).json({
      error: "User not found",
    });
  }

  return res.status(200).json(user);
});


//TRANSACTION ENDPOINTS 
// Endpoint 4: list transactions by user id
app.get("/api/v1/users/:userId/transactions", (req, res) => {
  const { userId } = req.params;

  const user = usersById.get(userId);
  if (!user) return res.status(404).json({ error: "User not found" });

  const txIds = txIdsByUserId.get(userId) ?? [];
  const transactions = txIds
    .map((txId) => txById.get(txId))
    .filter(Boolean);

  return res.json(transactions);
});

//Endpoint 5: Get transaction by transaction id (dev only)
app.get("/api/v1/transactions/:txId", (req, res) => {
  const tx = txById.get(req.params.txId);
  if (!tx) return res.status(404).json({ error: "Transaction not found" });
  return res.json(tx);
});

// Helpers for tx validation
function isNonEmptyString(x) {
  return typeof x === "string" && x.trim().length > 0;
}
function isPositiveNumber(x) {
  return typeof x === "number" && Number.isFinite(x) && x > 0;
}
function isIsoTimestamp(x) {
  return typeof x === "string" && !Number.isNaN(Date.parse(x));
}
function isValidCurrency(x) {
  return typeof x === "string" && /^[A-Z]{3}$/.test(x);
}
function isValidPaymentMethod(pm) {
  if (pm === undefined) return true;
  if (typeof pm !== "object" || pm === null) return false;
  return pm.type === "card_present" || pm.type === "online";
}


//Endpoint 6: Post a transaction for specific user
app.post("/api/v1/users/:userId/transactions", (req, res) => {
  const { userId } = req.params;

  // If user doesn't exist, treat as not found 
  const user = usersById.get(userId);
  if (!user) return res.status(404).json({ error: "User not found" });

  const {
    amount,
    currency,
    merchant,
    timestamp,
    location,
    payment_method,
    external_id,

    // Fraud fields NOT settable by this API
    fraud_score,
    is_fraud,
    scored_at,
    alerted_at,
  } = req.body ?? {};
  if (
    fraud_score !== undefined ||
    is_fraud !== undefined ||
    scored_at !== undefined ||
    alerted_at !== undefined
  ) {
    return res.status(400).json({
      error:
        "Fraud fields are not settable via this endpoint. Use this API only to add transactions.",
    });
  }

  if (!isPositiveNumber(amount)) {
    return res.status(400).json({ error: "amount must be a number > 0" });
  }

  const finalCurrency = currency === undefined ? "USD" : currency;
  if (!isValidCurrency(finalCurrency)) {
    return res.status(400).json({ error: "currency must be a 3-letter code like USD" });
  }

  if (!isNonEmptyString(merchant)) {
    return res.status(400).json({ error: "merchant must be a non-empty string" });
  }

  if (!isIsoTimestamp(timestamp)) {
    return res.status(400).json({ error: "timestamp must be a valid date-time string" });
  }

  if (location !== undefined) {
    if (typeof location !== "object" || location === null) {
      return res.status(400).json({ error: "location must be an object" });
    }
    // Placeholder: can validate lat/lng ranges later.
  }

  if (!isValidPaymentMethod(payment_method)) {
    return res.status(400).json({ error: 'payment_method.type must be "card_present" or "online"' });
  }

  if (external_id !== undefined && !isNonEmptyString(external_id)) {
    return res.status(400).json({ error: "external_id must be a non-empty string" });
  }

  // Placeholder uniqueness: prevent duplicate external_id per user 
  if (external_id) {
    if (!externalIdByUserId.has(userId)) externalIdByUserId.set(userId, new Set());
    const set = externalIdByUserId.get(userId);
    if (set.has(external_id)) {
      // Use 409 conflict pattern similar to user creation
      return res.status(409).json({ error: "external_id already exists for this user" });
    }
    set.add(external_id);
  }

  const txId = crypto.randomUUID();
  const created_at = new Date().toISOString();

  const tx = {
    id: txId,                 
    user_id: userId,         
    amount,
    currency: finalCurrency,  // default USD 
    merchant,
    timestamp,
    location: location ?? null,
    payment_method: payment_method ?? null,
    external_id: external_id ?? null,
    created_at,
    fraud_score: null,
    is_fraud: null,
    scored_at: null,
    alerted_at: null,
  };

  txById.set(txId, tx);
  if (!txIdsByUserId.has(userId)) txIdsByUserId.set(userId, []);
  txIdsByUserId.get(userId).push(txId);

  // Placeholder: later we can publish an event (SQS/SNS) for scoring + alerting
  // e.g. publishTransactionCreated(tx)

  return res.status(200).json(tx);
});





app.get("/health", (req, res) => res.json({ ok: true }));

//listen on port 3000 or set port
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API listening on http://localhost:${PORT}`));