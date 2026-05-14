import { chromium } from 'playwright';
import dotenv from 'dotenv';

dotenv.config({ path: '../.env' });

export class SearchManager {
    constructor() {
        this.proxyUrl = process.env.PROXY_URL;
    }

    _getBrowserConfig() {
        if (!this.proxyUrl) return { headless: true };
        
        const url = new URL(this.proxyUrl);
        return {
            headless: true,
            proxy: {
                server: `${url.protocol}//${url.host}`,
                username: url.username,
                password: url.password
            }
        };
    }

    async findSocialProfiles(name, company) {
        const browser = await chromium.launch(this._getBrowserConfig());
        const context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        });

        const platforms = [
            { name: 'linkedin', keyword: 'linkedin.com/in/', query: `${name} ${company} LinkedIn` },
            { name: 'instagram', keyword: 'instagram.com/', query: `${name} Instagram` },
            { name: 'twitter', keyword: 'twitter.com/', query: `${name} Twitter X` }
        ];

        const allProfiles = [];

        for (const platform of platforms) {
            try {
                const profiles = await this._searchOnPage(context, platform.query, platform.keyword, platform.name);
                allProfiles.push(...profiles);
            } catch (err) {
                console.error(`[Search] Failed for ${platform.name}:`, err.message);
            }
        }

        await browser.close();
        return [...new Set(allProfiles)];
    }

    async _searchOnPage(context, query, keyword, platformName) {
        const page = await context.newPage();
        // Block heavy resources
        await page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}', route => route.abort());

        try {
            const searchUrl = `https://www.bing.com/search?q=${encodeURIComponent(query)}`;
            console.log(`[Search] Querying Bing: ${query}`);
            await page.goto(searchUrl, { waitUntil: 'load', timeout: 60000 });
            await page.waitForTimeout(3000); // Settle

            const results = await page.evaluate(() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => ({
                        href: a.href,
                        text: a.innerText,
                        parentText: a.parentElement ? a.parentElement.innerText : ""
                    }))
                    .filter(item => item.href && item.href.startsWith('http'));
            });

            const found = [];
            for (const item of results) {
                const combinedText = (item.text + " " + item.parentText).toLowerCase();
                let isMatch = false;

                if (item.href.toLowerCase().includes(keyword)) {
                    isMatch = true;
                } else if (platformName === 'twitter' && (combinedText.includes('twitter') || combinedText.includes(' x ') || combinedText.includes('tweet'))) {
                    isMatch = True;
                } else if (combinedText.includes(platformName)) {
                    isMatch = true;
                }

                if (isMatch && !item.href.includes('bing.com')) {
                    let finalUrl = item.href;
                    // Decode Bing Redirect
                    if (item.href.includes('ck/a') && item.href.includes('&u=')) {
                        try {
                            const urlObj = new URL(item.href);
                            let u = urlObj.searchParams.get('u');
                            if (u) {
                                if (u.startsWith('a1')) u = u.substring(2);
                                let decoded = Buffer.from(u, 'base64').toString('utf-8');
                                if (decoded.includes('http')) finalUrl = decoded;
                            }
                        } catch (e) {}
                    }
                    found.push(finalUrl);
                    if (found.length >= 2) break;
                }
            }
            return found;
        } finally {
            await page.close();
        }
    }
}
