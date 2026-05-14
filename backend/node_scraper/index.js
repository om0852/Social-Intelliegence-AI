require('dotenv').config({ path: '../.env' });
const { chromium } = require('playwright');

const PROXY_URL = process.env.PROXY_URL;

async function runTest() {
    console.log(`Using Proxy: ${PROXY_URL}`);

    // Parse proxy parts
    let proxyConfig = null;
    if (PROXY_URL) {
        const url = new URL(PROXY_URL);
        proxyConfig = {
            server: `${url.protocol}//${url.host}`,
            username: url.username,
            password: url.password
        };
    }

    const browser = await chromium.launch({
        headless: false,
        proxy: proxyConfig
    });

    const context = await browser.newContext({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    });

    const page = await context.newPage();
    
    // Optimize: Block heavy resources to speed up slow proxy
    await page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}', route => route.abort());

    try {
        console.log('Checking IP via api.ipify.org...');
        await page.goto('https://api.ipify.org', { timeout: 60000 });
        const ip = await page.textContent('body');
        console.log(`My IP: ${ip.trim()}`);

        console.log('Searching DuckDuckGo Lite for Swati Gandhi LinkedIn...');
        // Use Lite version for speed
        const query = "Swati Gandhi LinkedIn Livemint";
        await page.goto(`https://duckduckgo.com/lite/?q=${encodeURIComponent(query)}`, { timeout: 90000, waitUntil: 'domcontentloaded' });
        
        await page.screenshot({ path: 'ddg_lite_node.png' });
        console.log('Screenshot saved to ddg_lite_node.png');
        
        const title = await page.title();
        console.log(`Page Title: ${title}`);

        const links = await page.$$eval('a', anchors => anchors.map(a => a.href));
        const linkedinLinks = links.filter(link => link.includes('linkedin.com/in/'));
        console.log(`Found ${linkedinLinks.length} LinkedIn links:`);
        linkedinLinks.slice(0, 5).forEach(l => console.log(` - ${l}`));

    } catch (error) {
        console.error('Test Failed:', error.message);
    } finally {
        await browser.close();
    }
}

runTest();
