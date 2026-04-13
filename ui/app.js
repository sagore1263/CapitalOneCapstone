const { useState, useEffect, useMemo } = React;

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));

// Mock API (in-memory)
const mockStore = { users: [], txs: [] };
const mockApi = {
  async createUser(payload) {
    const now = new Date().toISOString();
    const user = {
      id: uid(),
      created_at: now,
      phone_num: payload.phone_num ?? payload.phone_number,
      email: payload.email,
      threshold: Number(payload.threshold ?? 0.5),
      card_number: payload.card_number,
    };
    mockStore.users.push(user);
    return user;
  },
  async listUsers() { return [...mockStore.users]; },
  async createTransaction(userId, payload) {
    const now = new Date().toISOString();
    const tx = { id: uid(), user_id: userId, created_at: now, fraud_score: null, is_fraud: null, ...payload };
    mockStore.txs.push(tx);
    return tx;
  },
  clear() { mockStore.users = []; mockStore.txs = []; },
  seed() {
    this.clear();
    const samples = [
      { phone_num: "+15555550111", email: "ada@example.com", threshold: 0.35 },
      { phone_num: "+15555550222", email: "bruce@example.com", threshold: 0.6 },
    ];
    samples.forEach((u) => this.createUser(u));
  },
};

// Live API client (fetch)
const liveApi = (baseUrl) => ({
  async createUser(payload) {
    const res = await fetch(`${baseUrl}/users`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_number: payload.card_number,
        phone_number: payload.phone_number,
        email: payload.email,
        threshold: String(payload.threshold ?? 0.5),
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    return {
      id: data.cardNumber,
      phone_num: data.phoneNumber,
      email: data.email,
      threshold: Number(data.threshold ?? 0.5),
      created_at: data.createdAt,
      card_number: data.cardNumber,
      raw: data,
    };
  },
  async listUsers() {
    const res = await fetch(`${baseUrl}/users`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async createTransaction(userId, payload) {
    const res = await fetch(`${baseUrl}/users/${userId}/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
});

const toLocalInput = (date = new Date()) => {
  const pad = (n) => String(n).padStart(2, "0");
  const d = date;
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const FRAUD_MERCHANTS = [
  "ShadowCart Outlet",
  "Midnight Luxury Goods",
  "Orbit Ticket Exchange",
  "Flash Gadget Hub",
  "Velvet Wire Transfers"
];

const FRAUD_LOCATIONS = [
  "Miami, FL",
  "Las Vegas, NV",
  "Los Angeles, CA",
  "New York, NY",
  "Houston, TX"
];

function App() {
  const [useMock, setUseMock] = useState(false);
  const [baseUrl, setBaseUrl] = useState("https://rw7ca8yad8.execute-api.us-east-2.amazonaws.com/dev/api/v1");
  const [users, setUsers] = useState([]);
  const [logItems, setLogItems] = useState([]);
  const [txDefaults] = useState({ timestamp: toLocalInput() });

  const api = useMemo(() => (useMock ? mockApi : liveApi(baseUrl)), [useMock, baseUrl]);

  const log = (message, payload, status = "ok") => {
    setLogItems((prev) => [
      { id: uid(), ts: new Date().toLocaleTimeString(), message, payload, status },
      ...prev.slice(0, 49),
    ]);
  };

  const refreshUsers = async () => {
    if (!useMock) return;
    try {
      const list = await api.listUsers();
      setUsers(list);
      log("Fetched users", list);
    } catch (err) {
      log("Fetch users failed", err.message, "error");
    }
  };

  useEffect(() => { refreshUsers(); }, [api]);

  const handleCreateUser = async (payload) => {
    try {
      const user = await api.createUser(payload);
      log("User created", user);
      if (useMock) {
        refreshUsers();
      } else {
        setUsers((prev) => [user, ...prev.filter((existing) => existing.id !== user.id)]);
      }
    } catch (err) {
      log("User create failed", err.message, "error");
    }
  };

  const createSampleUsers = async () => {
    const samples = [
      {
        card_number: `411111111111${Math.floor(1000 + Math.random() * 9000)}`,
        phone_number: `+1555${Math.floor(1000000 + Math.random() * 9000000)}`,
        email: `ada-${uid().slice(0, 6)}@example.com`,
        threshold: 0.35,
      },
      {
        card_number: `422222222222${Math.floor(1000 + Math.random() * 9000)}`,
        phone_number: `+1555${Math.floor(1000000 + Math.random() * 9000000)}`,
        email: `bruce-${uid().slice(0, 6)}@example.com`,
        threshold: 0.6,
      },
    ];

    if (useMock) {
      mockApi.seed();
      refreshUsers();
      log("Created sample users");
      return;
    }

    for (const sample of samples) {
      await handleCreateUser(sample);
    }
  };

  const clearUsers = () => {
    if (!useMock) {
      setUsers([]);
      log("Cleared local user list");
      return;
    }

    mockApi.clear();
    refreshUsers();
    log("Cleared users & mock data");
  };

  const handleCreateTx = async (userId, payload) => {
    try {
      const tx = await api.createTransaction(userId, payload);
      log("Transaction submitted", tx);
    } catch (err) {
      log("Transaction failed", err.message, "error");
    }
  };

  return (
    <div className="page">
      <Header useMock={useMock} setUseMock={setUseMock} baseUrl={baseUrl} setBaseUrl={setBaseUrl} />
      <div className="grid">
        <Card>
          <h2>Create Account</h2>
          <UserForm onSubmit={handleCreateUser} />
        </Card>
        <Card>
          <h2>Submit Transaction</h2>
          <TxForm users={users} onSubmit={handleCreateTx} defaults={txDefaults} />
        </Card>
        <Card>
          <h2>Activity Log</h2>
          <p className="muted small">Shows API calls (mock or live) and responses.</p>
          <Log items={logItems} />
        </Card>
      </div>
      <Playground
        useMock={useMock}
        onSeed={createSampleUsers}
        onClear={clearUsers}
      />
    </div>
  );
}

const Header = ({ useMock, setUseMock, baseUrl, setBaseUrl }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
    <div>
      <h1>Fraud Detection Prototype</h1>
      <p className="lead">Create users and submit transactions against the deployed Lambda API, or switch back to mock mode for local-only testing.</p>
      <div className="pill">UI Mode: React + mockable API</div>
    </div>
    <div className="card" style={{ padding: "12px 16px" }}>
      <div className="inline">
        <span className="muted small">Mock API</span>
        <div className={"toggle " + (useMock ? "on" : "")} role="button" aria-label="toggle api mode" onClick={() => setUseMock((v) => !v)}></div>
        <span className="muted small">Live API</span>
      </div>
      <label style={{ marginTop: "12px" }}>Live API base URL</label>
      <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      <p className="muted small" style={{ marginTop: 6 }}>Uses the deployed API Gateway base URL for the Lambda-backed endpoints.</p>
    </div>
  </div>
);

const Playground = ({ useMock, onSeed, onClear }) => (
  <div className="card" style={{ margin: "16px 0" }}>
    <div className="row" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
      <div>
        <label>Data playground</label>
        <p className="muted small">Active mode: {useMock ? "Mock (in-memory)" : "Live (fetching API)"}</p>
      </div>
      <button type="button" onClick={onSeed}>Create random users</button>
      <button type="button" onClick={onClear} style={{ background: "none", color: "var(--text)", border: "1px solid var(--border)", boxShadow: "none" }}>Clear users</button>
    </div>
  </div>
);

const Card = ({ children }) => <div className="card">{children}</div>;

function UserForm({ onSubmit }) {
  const [form, setForm] = useState({ card_number: "", phone_number: "", email: "", threshold: 0.5 });
  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      onSubmit({ ...form, email: form.email || undefined });
      setForm({ card_number: "", phone_number: "", email: "", threshold: 0.5 });
    }}>
      <label>Card number</label>
      <input required placeholder="4111111111111111" value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
      <label>Phone number (E.164)</label>
      <input required placeholder="+15555551234" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
      <label>Email (optional)</label>
      <input type="email" placeholder="name@email.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <label>Alert threshold (0 - 1)</label>
      <input type="range" min="0" max="1" step="0.01" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: Number(e.target.value) })} />
      <div className="row small" style={{ marginTop: 4 }}>
        <span className="muted">Current: {form.threshold.toFixed(2)}</span>
        <span className="muted">Lower = more sensitive</span>
      </div>
      <button type="submit">Create User</button>
    </form>
  );
}

function TxForm({ users, onSubmit, defaults }) {
  const [form, setForm] = useState({
    user_id: "",
    amount: "",
    currency: "USD",
    merchant: "",
    timestamp: defaults.timestamp,
    payment_method: "online",
    external_id: "",
  });

  const randomTx = () => {
    if (!users.length) return null;
    const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
    const user_id = form.user_id || pick(users).id;
    const merchants = ["Contoso Books", "Northwind Market", "Globex Gadgets", "Blue Bottle", "ACME Co", "AeroFly"];
    const methods = ["online", "card_present"];
    const now = Date.now();
    const ts = new Date(now - Math.floor(Math.random() * 1000 * 60 * 60 * 24)).toISOString();
    return {
      user_id,
      payload: {
        amount: Number((Math.random() * 400 + 5).toFixed(2)),
        currency: "USD",
        merchant: pick(merchants),
        timestamp: ts,
        payment_method: { type: pick(methods) },
        external_id: Math.random() > 0.6 ? `ext-${uid().slice(0, 6)}` : undefined,
      },
    };
  };

  const randomFraudTx = () => {
    if (!users.length) return null;
    const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
    const user_id = form.user_id || pick(users).id;
    const now = Date.now();
    const ts = new Date(now - Math.floor(Math.random() * 1000 * 60 * 90)).toISOString();
    const amount = Number((Math.random() * 4500 + 4500).toFixed(2));
    const merchant = pick(FRAUD_MERCHANTS);
    const location = pick(FRAUD_LOCATIONS);

    return {
      user_id,
      payload: {
        amount,
        currency: "USD",
        merchant: `${merchant} - ${location}`,
        timestamp: ts,
        payment_method: { type: "online" },
        external_id: `fraud-${uid().slice(0, 8)}`,
      },
    };
  };

  useEffect(() => {
    if (!form.user_id && users.length) setForm((f) => ({ ...f, user_id: users[0].id }));
  }, [users]);

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      if (!form.user_id) return;
      onSubmit(form.user_id, {
        amount: Number(form.amount),
        currency: form.currency || "USD",
        merchant: form.merchant,
        timestamp: new Date(form.timestamp).toISOString(),
        payment_method: { type: form.payment_method },
        external_id: form.external_id || undefined,
      });
      setForm({ ...form, amount: "", merchant: "", external_id: "" });
    }}>
      <label>User</label>
      <select required value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })}>
        <option value="" disabled>Select user</option>
        {users.map((u) => <option key={u.id} value={u.id}>{u.phone_num} ({u.threshold ?? "?"})</option>)}
      </select>
      <label>Amount</label>
      <input required type="number" min="0.01" step="0.01" placeholder="120.55" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
      <label>Currency</label>
      <input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
      <label>Merchant</label>
      <input required placeholder="Contoso Books" value={form.merchant} onChange={(e) => setForm({ ...form, merchant: e.target.value })} />
      <label>Timestamp</label>
      <input required type="datetime-local" value={form.timestamp} onChange={(e) => setForm({ ...form, timestamp: e.target.value })} />
      <label>Payment method</label>
      <select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
        <option value="online">Online</option>
        <option value="card_present">Card present</option>
      </select>
      <label>External ID (optional)</label>
      <input placeholder="ext-123" value={form.external_id} onChange={(e) => setForm({ ...form, external_id: e.target.value })} />
      <div className="row" style={{ gap: 8 }}>
        <button type="submit">Send Transaction</button>
        <button type="button" onClick={() => {
          const tx = randomTx();
          if (!tx) return;
          setForm((prev) => ({ ...prev, user_id: tx.user_id }));
          onSubmit(tx.user_id, tx.payload);
        }}>Randomize & Send</button>
        <button
          type="button"
          className="danger-button"
          onClick={() => {
            const tx = randomFraudTx();
            if (!tx) return;
            setForm((prev) => ({
              ...prev,
              user_id: tx.user_id,
              amount: String(tx.payload.amount),
              currency: tx.payload.currency,
              merchant: tx.payload.merchant,
              timestamp: toLocalInput(new Date(tx.payload.timestamp)),
              payment_method: tx.payload.payment_method.type,
              external_id: tx.payload.external_id,
            }));
            onSubmit(tx.user_id, tx.payload);
          }}
        >
          Generate Fraudulent Transaction
        </button>
      </div>
    </form>
  );
}

const Log = ({ items }) => (
  <div className="log">
    {items.length === 0 && <p className="muted small">No events yet.</p>}
    {items.map((item) => (
      <div key={item.id} className="log-item">
        <div className="ts">{item.ts}</div>
        <div style={{ fontWeight: 600 }}>{item.message}</div>
        <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", margin: "6px 0 0", fontFamily: "Inter, monospace", fontSize: "0.9rem", color: item.status === "error" ? "#ff9b9b" : "#d6e8ff" }}>
{JSON.stringify(item.payload, null, 2)}
        </pre>
      </div>
    ))}
  </div>
);

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
