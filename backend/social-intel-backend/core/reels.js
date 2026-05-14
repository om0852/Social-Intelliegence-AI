import axios from 'axios';

export class ReelsService {
    constructor() {
        const token = process.env.APIFY_TOKEN || "YOUR_APIFY_TOKEN";
        this.datasetUrl = `https://api.apify.com/v2/datasets/lZukKxCRwtOmffQ5o/items?token=${token}`;
    }

    async getReelData(targetUrl) {
        console.log(`[ReelsService] Searching for Reel: ${targetUrl}`);
        try {
            const response = await axios.get(this.datasetUrl);
            const items = response.data;
            
            // Normalize target URL (remove trailing slashes, etc.)
            const normalizedTarget = targetUrl.split('?')[0].replace(/\/$/, "");
            
            const reel = items.find(item => {
                const normalizedItemUrl = item.url.split('?')[0].replace(/\/$/, "");
                return normalizedItemUrl === normalizedTarget;
            });

            if (!reel) {
                throw new Error("Reel data not found in dataset. Ensure the URL is correct and has been scraped.");
            }

            return {
                caption: reel.caption,
                owner: reel.ownerUsername,
                ownerFullName: reel.ownerFullName,
                likes: reel.likesCount,
                views: reel.videoViewCount,
                plays: reel.videoPlayCount,
                timestamp: reel.timestamp,
                thumbnail: reel.displayUrl,
                videoUrl: reel.videoUrl,
                location: reel.locationName,
                music: reel.musicInfo
            };
        } catch (error) {
            console.error(`[ReelsService] Error:`, error.message);
            throw error;
        }
    }
}
