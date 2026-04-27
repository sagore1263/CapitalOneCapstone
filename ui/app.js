const { useState, useEffect } = React;

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));

const apiClient = (baseUrl) => ({
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

const TX_CATEGORIES = [
  "food_dining", "gas_transport", "grocery_net", "grocery_pos",
  "health_fitness", "home", "kids_pets", "misc_net", "misc_pos",
  "personal_care", "shopping_net", "shopping_pos", "travel", "entertainment"
];

const SAMPLE_FIRST_NAMES = ["James", "Maria", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "David", "Barbara"];
const SAMPLE_LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Taylor"];
const SAMPLE_JOBS = ["Engineer", "Teacher", "Accountant", "Nurse", "Manager", "Designer", "Analyst", "Chef", "Writer", "Lawyer"];
const SAMPLE_STREETS = ["123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm Blvd", "654 Maple Dr"];
const SAMPLE_CITIES_STATES = [
  { city: "Austin",      state: "TX", zip: "78701", lat: 30.2672, lng: -97.7431, pop: 961855 },
  { city: "Denver",      state: "CO", zip: "80201", lat: 39.7392, lng: -104.9903, pop: 715522 },
  { city: "Atlanta",     state: "GA", zip: "30301", lat: 33.7490, lng: -84.3880, pop: 498715 },
  { city: "Seattle",     state: "WA", zip: "98101", lat: 47.6062, lng: -122.3321, pop: 737255 },
  { city: "Phoenix",     state: "AZ", zip: "85001", lat: 33.4484, lng: -112.0740, pop: 1608139 },
  { city: "Chicago",     state: "IL", zip: "60601", lat: 41.8781, lng: -87.6298, pop: 2696555 },
  { city: "Boston",      state: "MA", zip: "02101", lat: 42.3601, lng: -71.0589, pop: 675647 },
  { city: "Portland",    state: "OR", zip: "97201", lat: 45.5051, lng: -122.6750, pop: 652503 },
];

const randUsLat  = () => parseFloat((Math.random() * 24 + 25).toFixed(6));
const randUsLng  = () => parseFloat((Math.random() * 57 - 125).toFixed(6));
const pickRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];

function App() {
  const [baseUrl, setBaseUrl] = useState("https://rw7ca8yad8.execute-api.us-east-2.amazonaws.com/dev/api/v1");
  const [users, setUsers] = useState([]);
  const [logItems, setLogItems] = useState([]);
  const [txDefaults] = useState({ timestamp: toLocalInput() });

  const api = apiClient(baseUrl);

  const log = (message, payload, status = "ok") => {
    setLogItems((prev) => [
      { id: uid(), ts: new Date().toLocaleTimeString(), message, payload, status },
      ...prev.slice(0, 49),
    ]);
  };

  const handleCreateUser = async (payload) => {
    try {
      const user = await api.createUser(payload);
      log("User created", user);
      setUsers((prev) => [user, ...prev.filter((existing) => existing.id !== user.id)]);
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

    for (const sample of samples) {
      await handleCreateUser(sample);
    }
  };

  const clearUsers = () => {
    setUsers([]);
    log("Cleared local user list");
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
      <Header baseUrl={baseUrl} setBaseUrl={setBaseUrl} />
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
          <p className="muted small">Shows API calls and responses from the deployed backend.</p>
          <Log items={logItems} />
        </Card>
      </div>
      <Playground
        onSeed={createSampleUsers}
        onClear={clearUsers}
      />
    </div>
  );
}

const Header = ({ baseUrl, setBaseUrl }) => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px", flexWrap: "wrap" }}>
    <div>
      <h1>Capital One Fraud Detection</h1>
      <p className="lead">Create users and submit transactions against the deployed Lambda API.</p>
      <div className="pill">UI Mode: Live API</div>
    </div>
    <div className="card" style={{ padding: "12px 16px" }}>
      <label style={{ marginTop: "12px" }}>Live API base URL</label>
      <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      <p className="muted small" style={{ marginTop: 6 }}>Uses the deployed API Gateway base URL for the Lambda-backed endpoints.</p>
    </div>
  </div>
);

const Playground = ({ onSeed, onClear }) => (
  <div className="card" style={{ margin: "16px 0" }}>
    <div className="row" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
      <div>
        <label>Data playground</label>
        <p className="muted small">Creates sample users through the deployed API and clears the local UI list.</p>
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
    merchant: "",
    category: "shopping_net",
    transactionTimestamp: defaults.timestamp,
    firstName: "",
    lastName: "",
    gender: "M",
    dateOfBirth: "",
    job: "",
    street: "",
    city: "",
    state: "",
    zipCode: "",
  });

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const buildTxPayload = (user_id, overrides = {}) => {
    const user = users.find(u => u.id === user_id);
    const location = pickRandom(SAMPLE_CITIES_STATES);
    const ts = overrides.ts || new Date(Date.now() - Math.floor(Math.random() * 86400000)).toISOString();
    return {
      cardNumber: user?.card_number || user_id,
      transactionTimestamp: ts,
      unixTime: Math.floor(new Date(ts).getTime() / 1000),
      amount: overrides.amount || Number((Math.random() * 400 + 5).toFixed(2)),
      merchant: overrides.merchant || pickRandom(["Contoso Books", "Northwind Market", "Globex Gadgets", "Blue Bottle", "ACME Co", "AeroFly"]),
      category: overrides.category || pickRandom(TX_CATEGORIES),
      firstName: pickRandom(SAMPLE_FIRST_NAMES),
      lastName: pickRandom(SAMPLE_LAST_NAMES),
      gender: pickRandom(["M", "F"]),
      dateOfBirth: `${1950 + Math.floor(Math.random() * 40)}-${String(Math.floor(Math.random() * 12) + 1).padStart(2, "0")}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, "0")}`,
      job: pickRandom(SAMPLE_JOBS),
      street: pickRandom(SAMPLE_STREETS),
      city: location.city,
      state: location.state,
      zipCode: location.zip,
      cityPopulation: location.pop,
      customerLatitude: location.lat,
      customerLongitude: location.lng,
      merchantLatitude: randUsLat(),
      merchantLongitude: randUsLng(),
      isFraud: overrides.isFraud || 0,
      ...overrides.extra,
    };
  };

  const randomTx = () => {
    if (!users.length) return null;
    const user_id = form.user_id || pickRandom(users).id;
    return { user_id, payload: buildTxPayload(user_id) };
  };

  const randomFraudTx = () => {
    if (!users.length) return null;
    const user_id = form.user_id || pickRandom(users).id;
    const location = pickRandom(FRAUD_LOCATIONS);
    const merchant = `${pickRandom(FRAUD_MERCHANTS)} - ${location}`;
    const ts = new Date(Date.now() - Math.floor(Math.random() * 5400000)).toISOString();
    return {
      user_id,
      payload: buildTxPayload(user_id, {
        amount: Number((Math.random() * 4500 + 4500).toFixed(2)),
        merchant,
        category: pickRandom(["shopping_net", "misc_net", "travel"]),
        ts,
        isFraud: 1,
      }),
    };
  };

  useEffect(() => {
    if (!form.user_id && users.length) setForm((f) => ({ ...f, user_id: users[0].id }));
  }, [users]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.user_id) return;
    const user = users.find(u => u.id === form.user_id);
    const ts = new Date(form.transactionTimestamp).toISOString();
    const location = SAMPLE_CITIES_STATES.find(l => l.city === form.city) || SAMPLE_CITIES_STATES[0];
    onSubmit(form.user_id, {
      cardNumber: user?.card_number || form.user_id,
      transactionTimestamp: ts,
      unixTime: Math.floor(new Date(ts).getTime() / 1000),
      amount: Number(form.amount),
      merchant: form.merchant,
      category: form.category,
      firstName: form.firstName,
      lastName: form.lastName,
      gender: form.gender,
      dateOfBirth: form.dateOfBirth,
      job: form.job,
      street: form.street,
      city: form.city,
      state: form.state,
      zipCode: form.zipCode,
      cityPopulation: location.pop || 500000,
      customerLatitude: location.lat || randUsLat(),
      customerLongitude: location.lng || randUsLng(),
      merchantLatitude: randUsLat(),
      merchantLongitude: randUsLng(),
      isFraud: 0,
    });
    setForm((f) => ({ ...f, amount: "", merchant: "" }));
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>User</label>
      <select required value={form.user_id} onChange={set("user_id")}>
        <option value="" disabled>Select user</option>
        {users.map((u) => <option key={u.id} value={u.id}>{u.phone_num} ({u.threshold ?? "?"})</option>)}
      </select>

      <label>Amount</label>
      <input required type="number" min="0.01" step="0.01" placeholder="120.55" value={form.amount} onChange={set("amount")} />
      <label>Merchant</label>
      <input required placeholder="Contoso Books" value={form.merchant} onChange={set("merchant")} />
      <label>Category</label>
      <select value={form.category} onChange={set("category")}>
        {TX_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
      </select>
      <label>Timestamp</label>
      <input required type="datetime-local" value={form.transactionTimestamp} onChange={set("transactionTimestamp")} />

      <p className="muted small" style={{ marginTop: 12 }}>Customer info</p>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>First name</label>
          <input required placeholder="Jane" value={form.firstName} onChange={set("firstName")} />
        </div>
        <div style={{ flex: 1 }}>
          <label>Last name</label>
          <input required placeholder="Doe" value={form.lastName} onChange={set("lastName")} />
        </div>
      </div>
      <div className="row">
        <div style={{ flex: 1 }}>
          <label>Gender</label>
          <select value={form.gender} onChange={set("gender")}>
            <option value="M">M</option>
            <option value="F">F</option>
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label>Date of birth</label>
          <input required type="date" value={form.dateOfBirth} onChange={set("dateOfBirth")} />
        </div>
      </div>
      <label>Job</label>
      <input required placeholder="Engineer" value={form.job} onChange={set("job")} />

      <p className="muted small" style={{ marginTop: 12 }}>Address</p>
      <label>Street</label>
      <input required placeholder="123 Main St" value={form.street} onChange={set("street")} />
      <div className="row">
        <div style={{ flex: 2 }}>
          <label>City</label>
          <input required placeholder="Austin" value={form.city} onChange={set("city")} />
        </div>
        <div style={{ flex: 1 }}>
          <label>State</label>
          <input required placeholder="TX" maxLength={2} value={form.state} onChange={set("state")} />
        </div>
        <div style={{ flex: 1 }}>
          <label>ZIP</label>
          <input required placeholder="78701" value={form.zipCode} onChange={set("zipCode")} />
        </div>
      </div>

      <div className="row" style={{ gap: 8, marginTop: 12 }}>
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
            setForm((prev) => ({ ...prev, user_id: tx.user_id, amount: String(tx.payload.amount), merchant: tx.payload.merchant }));
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
