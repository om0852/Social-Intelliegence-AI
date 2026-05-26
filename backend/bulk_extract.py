import asyncio
import json
import logging
import sys
import os
import httpx

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

urls = [
    "https://thenewsmill.com/2026/05/ncp-sp-mla-rohit-pawar-vows-protest-against-rising-fuel-prices/",
    "https://www.aninews.in/news/national/politics/we-will-protest-ncp-sp-mla-rohit-pawar-warns-centre-amid-surging-fuel-costs20260525163937/",
    "https://newsroompanama.com/2026/05/25/10-best-ai-slides-generators-for-fast-professional-presentations/",
    "https://www.theglobeandmail.com/investing/markets/stocks/KO/pressreleases/2117157/can-pepsicos-innovation-push-reignite-its-growth-in-2026/",
    "https://www.cantabriadirecta.es/la-virgen-de-mar-en-imagenes-noticias-cantabria-virgen-del-mar/",
    "https://www.ptinews.com/story/business/crude-oil-tumbles-over-4-pc-in-futures-trade-on-hopes-of-hormuz-breakthrough/3701738",
    "https://shopping.yahoo.com/beauty/nails/articles/23-june-short-nail-ideas-160000558.html",
    "https://whky.com/attorney-general-jeff-jackson-urges-north-carolinians-to-protect-personal-information-following-large-canvas-data-breach/",
    "https://www.aninews.in/news/business/indias-performance-nutrition-market-sees-growth-as-demand-for-high-stimulant-pre-workout-supplements-rises20260525160329/",
    "https://www.business-standard.com/industry/banking/credit-card-spends-rise-7-to-1-97-trillion-in-april-2026-rbi-data-126052501727_1.html",
    "https://timesofindia.indiatimes.com/city/mumbai/no-decision-yet-by-state-on-cutting-vat-oppn-slams-latest-fuel-rate-hike/articleshow/131313499.cms",
    "https://www.tv9marathi.com/maharashtra/mla-rohit-pawar-demands-postponement-of-mlc-election-amid-fuel-crisis-1676110.html",
    "https://univest.in/blogs/axis-bank-futures-options-prediction-for-tomorrow-26-may-2026-closes-at-rs-1311-20-2-01-on-nse-monthly-expiry-eve",
    "https://m.economictimes.com/tech/startups/cyber-alert-companies-rush-to-fortify-systems/articleshow/131295135.cms",
    "https://stockholmcf.org/turkeys-top-court-annuls-digital-search-law-over-privacy-safeguards/",
    "https://www.nj.com/news/2026/05/a-rare-blue-moon-is-on-the-way-but-heres-the-truth-about-its-color.html",
    "https://www.business-standard.com/amp/industry/banking/credit-card-spends-rise-7-to-1-97-trillion-in-april-2026-rbi-data-126052501727_1.html",
    "https://www.americanthinker.com/articles/2026/05/iran_is_playing_a_risky_game_with_its_oil_fields.html",
    "https://thefocusindia.com/maharashtra-news/rohit-pawar-demands-postponement-of-elections-305302/",
    "https://maharashtratimes.com/maharashtra/mumbai-news/umesh-patil-on-rohit-pawar/videoshow/131308049.cms",
    "https://buyhatke.com/lookalike/myntra-snitch-men-slim-fit-solid-mandarin-collar-pure-cotton-casual-shirt-price-in-india-111-16225889",
    "https://www.thestreet.com/retail/new-walmart-soda-line-takes-on-coca-cola-and-pepsico",
    "https://migijon.com/atencion-simulacro-las-sirenas-sonaran-este-miercoles-en-la-zona-oeste-de-gijon-y-carreno/",
    "https://www.punekarnews.in/pune-woman-records-man-making-obscene-gestures-at-chinchwad-brt-stop-accused-arrested/",
    "https://peoplesartist.org/2026/alexander-campa",
    "https://www.coca-cola.com/us/en/offerings/coca-cola/america250/celebrate",
    "https://www.wbtv.com/video/2026/05/25/daniel-suarez-wins-emotional-2026-coca-cola-600-charlotte-motor-speedway/",
    "https://www.msn.com/en-in/money/markets/daily-robbery-mallikarjun-kharge-slams-modi-government-over-4th-fuel-price-hike-in-2-weeks/ar-AA240cvc?apiversion=v2&domshim=1&noservercache=1&noservertelemetry=1&batchservertelemetry=1&renderwebcomponents=1&wcseo=1",
    "https://timesofindia.indiatimes.com/city/mumbai/rohit-pawar-slams-charity-commissioner-over-tata-trusts-order-questions-ties-to-govt/articleshow/131312332.cms",
    "https://www.punekarnews.in/pune-pcmc-imposes-curbs-on-tours-vehicle-use-to-conserve-energy-amid-west-asia-tensions/",
    "https://www.cameparkare.com/global/sites/cameparkare.com.global/files/webform/green-motion-campa-cola-espana51.pdf",
    "https://standardbredcanada.ca/news/5-25-26/tracking-2026-pepsi-north-america-cup-contenders.html",
    "https://medium.com/@sardarazizi780/i-wasted-6-months-learning-canva-then-ai-showed-me-i-was-designing-completely-backwards-1598acf6ced2",
    "https://sachkahoonpunjabi.com/world-news/what-went-wrong-for-punjab-kings-after-strong-start/article-57316",
    "https://www.tiktok.com/@smarthomeuk/video/7643842920348454166",
    "https://www.theguardian.com/sport/2026/may/25/suarez-pays-tribute-to-kyle-busch-after-coca-cola-600-win-this-one-is-for-him",
    "https://www.punekarnews.in/pune-pcmc-gives-shopkeepers-15-day-deadline-to-remove-encroachments/",
    "https://samais.com.br/publicacoes/como-a-pepsico-usou-os-dados-do-walmart-para-repensar-seu-manual-de-lancamentos",
    "https://sg.finance.yahoo.com/news/worth-investing-axon-axon-based-133004941.html",
    "https://www.essence.com/lifestyle/summer-party-ideas-amber-mayfield-hewett/",
    "https://sachkahoonpunjabi.com/state/punjab/galadas-major-operation-demolishes-five-unauthorized-colonies/article-57327",
    "https://www.georgeherald.com/Municipal-Notices/Article/General-Notices/collection-of-wood-chips-202605250310",
    "https://www.tv9marathi.com/maharashtra/rohit-pawar-slams-eknath-shinde-be-upset-over-inflation-maharashtra-politics-1676119.html",
    "https://www.syracuse.com/advice/2026/05/miss-manners-is-it-too-much-to-ask-of-you-an-employer-to-call-back-a-prospective-employee.html?outputType=amp",
    "https://www.punekarnews.in/corporator-nivrutti-bandal-proposes-ppp-model-to-solve-water-crisis-in-south-pune/",
    "https://www.jezebel.com/i-tried-dunkins-new-dirty-pepsi-and-i-cant-stop-shaking-and-slamming-my-head-against-the-wall",
    "https://www.msn.com/en-in/money/news/petrol-diesel-prices-hiked-for-fourth-time-in-10-days-check-latest-fuel-prices/ar-AA23XYge?gemSnapshotKey=GMD60A46D7-snapshot-13&apiversion=v2&domshim=1&noservercache=1&noservertelemetry=1&batchservertelemetry=1&renderwebcomponents=1&wcseo=1"
]

async def process_urls():
    output_file = "bulk_results.json"
    results = []
    
    # Load existing results so we append rather than overwrite
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            logger.info(f"Loaded {len(results)} existing entries from {output_file}. Appending new URLs...")
        except Exception as e:
            logger.warning(f"Could not load existing {output_file}, starting fresh. Error: {e}")
    
    for i, url in enumerate(urls):
        logger.info(f"\n=============================================")
        logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
        logger.info(f"=============================================")
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post("http://127.0.0.1:8000/extract", json={"url": url})
                response.raise_for_status()
                result = response.json()
            
            results.append({
                "url": url,
                "result": result
            })
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error processing {url}: {e.response.text}")
            results.append({
                "url": url,
                "result": {"success": False, "error": e.response.text}
            })
        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
            results.append({
                "url": url,
                "result": {"success": False, "error": str(e)}
            })
            
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Successfully saved progress to {output_file} (Total: {len(results)})")
        
        if i < len(urls) - 1:
            await asyncio.sleep(2)
            
if __name__ == "__main__":
    asyncio.run(process_urls())
    print(f"All done! Final results appended to bulk_results.json")
