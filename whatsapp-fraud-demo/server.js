//removed credentials since this is on AWS server now. 
import express from "express";
import axios from "axios";
import dotenv from "dotenv";

dotenv.config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const META_ACCESS_TOKEN = process.env.META_ACCESS_TOKEN;
const META_PHONE_NUMBER_ID = process.env.META_PHONE_NUMBER_ID;
const META_VERIFY_TOKEN = process.env.META_VERIFY_TOKEN;

const users = [
  {
    id: 1,
    name: "Test User",
    phone: process.env.TEST_USER_PHONE,
    fraudThreshold: 0.7,
  },
];

const transactions = [];
const pendingAlertsByPhone = new Map();

async function sendWhatsAppText(to, body) {
  const url = `https://graph.facebook.com/v25.0/${META_PHONE_NUMBER_ID}/messages`;

  const payload = {
    messaging_product: "whatsapp",
    to,
    type: "text",
    text: {
      body,
    },
  };

  const response = await axios.post(url, payload, {
    headers: {
      Authorization: `Bearer ${META_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
    },
  });

  console.log("WhatsApp text send response:", response.data);
  return response.data;
}

function scoreTransaction() {
  return Math.random();
}

app.post("/transactions", async (req, res) => {
  try {
    const { userId, merchant, amount } = req.body;

    const user = users.find((u) => u.id === userId);
    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }

    const transaction = {
      id: transactions.length + 1,
      userId,
      merchant,
      amount,
      fraudScore: 0,
      isFraud: false,
      status: "created",
      whatsappMessageId: null,
    };

    transaction.fraudScore = scoreTransaction();
    transactions.push(transaction);

    if (transaction.fraudScore >= user.fraudThreshold) {
      const msg =
        `🚨 Fraud Alert\n\n` +
        `Transaction #${transaction.id}\n` +
        `Merchant: ${merchant}\n` +
        `Amount: $${Number(amount).toFixed(2)}\n` +
        `Fraud Score: ${transaction.fraudScore.toFixed(2)}\n\n` +
        `Reply YES if this was fraud.\n` +
        `Reply NO if this was not fraud.`;

      const sendResult = await sendWhatsAppText(user.phone, msg);

      pendingAlertsByPhone.set(user.phone, transaction.id);
      transaction.status = "alert_sent";
      transaction.whatsappMessageId = sendResult?.messages?.[0]?.id || null;
    }

    return res.json({
      message: "Transaction processed",
      transaction,
    });
  } catch (error) {
    console.error(
      "Error creating transaction:",
      error?.response?.data || error.message
    );

    return res.status(500).json({
      error: "Failed to process transaction",
      details: error?.response?.data || error.message,
    });
  }
});

app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  console.log("VERIFY REQUEST:", { mode, token, challenge });

  if (mode === "subscribe" && token === META_VERIFY_TOKEN) {
    return res.status(200).send(challenge);
  }

  return res.sendStatus(403);
});

app.post("/webhook", (req, res) => {
  try {
    console.log("WEBHOOK BODY:", JSON.stringify(req.body, null, 2));

    const entry = req.body?.entry?.[0];
    const change = entry?.changes?.[0];
    const value = change?.value;

    if (value?.statuses?.length) {
      console.log("Message status update:", value.statuses);
    }

    const messages = value?.messages;
    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      return res.sendStatus(200);
    }

    const message = messages[0];
    const from = message.from;
    const text = message?.text?.body?.trim()?.toUpperCase();

    console.log("Incoming user message:", { from, text });

    const transactionId = pendingAlertsByPhone.get(from);
    if (!transactionId) {
      console.log("No pending alert found for phone:", from);
      return res.sendStatus(200);
    }

    const transaction = transactions.find((t) => t.id === transactionId);
    if (!transaction) {
      console.log("Transaction not found for pending alert:", transactionId);
      return res.sendStatus(200);
    }

    if (text === "YES") {
      transaction.isFraud = true;
      transaction.status = "confirmed_fraud";
      pendingAlertsByPhone.delete(from);
      console.log(`Transaction ${transaction.id} marked as fraud`);
    } else if (text === "NO") {
      transaction.isFraud = false;
      transaction.status = "confirmed_not_fraud";
      pendingAlertsByPhone.delete(from);
      console.log(`Transaction ${transaction.id} marked as not fraud`);
    } else {
      console.log("Ignoring unsupported reply:", text);
    }

    return res.sendStatus(200);
  } catch (error) {
    console.error("Webhook error:", error?.response?.data || error.message);
    return res.sendStatus(500);
  }
});

app.get("/transactions", (req, res) => {
  res.json(transactions);
});

app.get("/", (req, res) => {
  res.send("Server is running");
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});