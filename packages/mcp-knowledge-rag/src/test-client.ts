import { queryKnowledgeBase } from './index';

async function main() {
    const query = process.argv[2] || 'AI and machine learning';
    console.log(`Querying RAG database for: "${query}"...`);
    try {
        const results = await queryKnowledgeBase(query, 3, 0.4);
        console.log(`\nFound ${results.length} matches:`);

        if (results.length === 0) {
            console.log('No matching emails found.');
            return;
        }

        results.forEach((res, index) => {
            console.log(
                `\n--- Result ${index + 1} (Similarity: ${(res.similarity * 100).toFixed(1)}%) ---`,
            );
            console.log(`Sender: ${res.sender}`);
            console.log(`Subject: ${res.subject}`);
            console.log(`Date: ${res.received_at}`);
            console.log(`Body snippet: ${res.body?.substring(0, 300)}...`);
        });
    } catch (error) {
        console.error('Error executing query:', error);
    }
}

main();
