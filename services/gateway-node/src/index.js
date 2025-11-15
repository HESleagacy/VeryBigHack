// gateway-node/src/index.js

require('dotenv').config({ path: '../../.env' }); // Correct path to your root .env
const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const axios = require('axios');
const { MongoClient, ServerApiVersion } = require('mongodb');

const app = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());
app.use(morgan('dev'));

// --- Database Connection ---
const mongoUrl = process.env.MONGO_URL || process.env.MONGO_URI;

if (!mongoUrl) {
  console.error("❌ Missing MONGO_URL or MONGO_URI in environment!");
  process.exit(1);
}

const mongoClient = new MongoClient(mongoUrl, {
  serverApi: {
    version: ServerApiVersion.v1,
    strict: true,
    deprecationErrors: true,
  }
});

let db;

async function connectDB() {
  try {
    await mongoClient.connect();
    db = mongoClient.db(process.env.DB_NAME);
    await db.command({ ping: 1 });
    console.log("✅ Connected to MongoDB successfully!");

    // Ensure collections exist and indexes
    await db.collection('users').createIndex({ userId: 1 }, { unique: true });
    await db.collection('query_logs').createIndex({ timestamp: -1 });
    await db.collection('threat_logs').createIndex({ timestamp: -1 });

    console.log("✅ Collections and indexes ensured.");
  } catch (err) {
    console.error("❌ Failed to connect to MongoDB:", err);
    process.exit(1);
  }
}

// --- API Endpoints ---

// Health Check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'gateway-node' });
});

// 1. Main Prompt Endpoint
app.post('/api/v1/prompt', async (req, res) => {
  const { userId, prompt } = req.body;
  if (!userId || !prompt) {
    return res.status(400).json({ error: 'userId and prompt are required' });
  }

  try {
    let user = await db.collection('users').findOne({ userId });
    if (!user) {
      user = {
        userId,
        suspicion_score: 0.0,
        is_human_verified: false,
        last_seen: new Date(),
      };
      await db.collection('users').insertOne(user);
    }

    const score = user.suspicion_score || 0;

    // --- 3-TIER DEFENSE LOGIC ---
    // Tier 3: Perma-block
    if (score >= 0.95) {
      console.log(`[${userId}] BLOCKED (Tier 3) - Score: ${score}`);
      return res.status(403).json({ error: 'Access Forbidden: Account flagged for malicious activity.' });
    }

    // Tier 2: Temp-block
    if (score >= 0.8) {
      console.log(`[${userId}] RATE LIMITED (Tier 2) - Score: ${score}`);
      return res.status(429).json({ error: 'Too many requests: Human verification required.' });
    }

    // Tier 1: Default, forward to wrapper
    console.log(`[${userId}] ROUTING TO WRAPPER (Tier 1) - Score: ${score}`);
    const wrapperResponse = await axios.post(process.env.WRAPPERS_URL, { userId, prompt });
    res.status(200).json(wrapperResponse.data);

  } catch (error) {
    console.error("Error in /prompt endpoint:", error.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// 2. System History Endpoint
app.get('/api/v1/system-history', async (req, res) => {
  try {
    const logs = await db.collection('query_logs').find().sort({ timestamp: -1 }).limit(50).toArray();
    res.status(200).json(logs);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch system history' });
  }
});

// 3. Users List Endpoint
app.get('/api/v1/users', async (req, res) => {
  try {
    const users = await db.collection('users').find().sort({ last_seen: -1 }).limit(50).toArray();
    res.status(200).json(users);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch users' });
  }
});

// 4. Threat Log Endpoint
app.get('/api/v1/threat-log', async (req, res) => {
  try {
    const threats = await db.collection('threat_logs').find().sort({ timestamp: -1 }).limit(50).toArray();
    res.status(200).json(threats);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch threat log' });
  }
});

// --- Start Server ---
connectDB().then(() => {
  app.listen(port, () => {
    console.log(`🛡️  Sentinel Gateway listening on http://localhost:${port}`);
  });
});

