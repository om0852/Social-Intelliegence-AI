import axios from 'axios';

async function testReel() {
    const url = 'https://www.instagram.com/p/DSqIuPzCNOS/';
    
    console.log('Testing Reel Extraction Endpoint...');
    try {
        const response = await axios.post('http://localhost:4000/extract-reel', { url });
        console.log('SUCCESS!');
        console.log(JSON.stringify(response.data, null, 2));
    } catch (error) {
        console.error('FAILED:', error.response?.data || error.message);
    }
}

testReel();
