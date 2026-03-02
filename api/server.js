import express from "express";
import crypto from "crypto";

const app = express();
app.use(express.json());


/**
 * usersById: Map<userId, userObj>
 * userIdByPhone: Map<phone_num, userId>
 */
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


// Endpoint 2: list all users
// GET /api/v1/users
app.get("/api/v1/users", (req, res) => {
  return res.json(Array.from(usersById.values()));
});

//Endpoint 3: select user by id
// GET /api/v1/users/:userId
app.get("/api/v1/users/:userId", (req, res) => {
  const user = usersById.get(req.params.userId);
  if (!user) return res.status(404).json({ error: "User not found" });
  return res.json(user);
});


app.get("/health", (req, res) => res.json({ ok: true }));

//listen on port 3000 or set port
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`API listening on http://localhost:${PORT}`));