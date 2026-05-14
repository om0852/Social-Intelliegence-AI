import { chromium } from 'playwright';

export class Scraper {
    async scrape(url) {
        const browser = await chromium.launch({ headless: true });
        const context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        });
        const page = await context.newPage();
        
        try {
            console.log(`[Scraper] Navigating to ${url}`);
            await page.goto(url, { waitUntil: 'load', timeout: 60000 });
            
            const title = await page.title();
            const content = await page.evaluate(() => {
                // Basic cleanup of article text
                const scripts = document.querySelectorAll('script, style, nav, footer');
                scripts.forEach(s => s.remove());
                return document.body.innerText.substring(0, 5000); // Limit for AI
            });

            return { url, title, content };
        } finally {
            await browser.close();
        }
    }
}
