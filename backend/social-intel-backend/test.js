import axios from 'axios';

async function testPipeline() {
    const url = 'https://www.livemint.com/news/us-news/trump-promised-to-hold-30-000-migrants-in-73-mn-guantanamo-center-a-year-later-it-holds-only-six-detainees-report-11778690247596.html';
    
    console.log('Testing Social Intelligence Backend...');
    try {
        const response = await axios.post('http://localhost:4000/extract', { url });
        console.log('SUCCESS!');
        console.log(JSON.stringify(response.data, null, 2));
    } catch (error) {
        console.error('FAILED:', error.response?.data || error.message);
    }
}

testPipeline();
