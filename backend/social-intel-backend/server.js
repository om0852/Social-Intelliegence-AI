import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { Orchestrator } from './core/orchestrator.js';
import { ReelsService } from './core/reels.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());

const orchestrator = new Orchestrator();
const reelsService = new ReelsService();

app.post('/extract-reel', async (req, res) => {
    const { url } = req.body;
    if (!url) {
        return res.status(400).json({ success: false, error: 'Reel URL is required' });
    }

    console.log(`[Server] Received Reel extraction request for: ${url}`);
    try {
        const result = await reelsService.getReelData(url);
        res.json({ success: true, data: result });
    } catch (error) {
        console.error(`[Server] Reel extraction failed:`, error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.post('/extract', async (req, res) => {
    const { url } = req.body;
    if (!url) {
        return res.status(400).json({ success: false, error: 'URL is required' });
    }

    console.log(`[Server] Received extraction request for: ${url}`);
    try {
        const result = await orchestrator.runPipeline(url);
        res.json({ success: true, data: result });
    } catch (error) {
        console.error(`[Server] Extraction failed:`, error);
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(port, () => {
    console.log(`[Server] Social Intelligence Backend running on port ${port}`);
});
