import json
import boto3

class OutcomeExtractor:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
    
    def extract_outcomes(self, pdf_bytes):
        """Extract outcomes from PDF bytes using AWS Bedrock."""
        # Use Bedrock Converse API with PDF document directly
        response = self.bedrock.converse(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "document": {
                                "format": "pdf",
                                "name": "document",
                                "source": {
                                    "bytes": pdf_bytes
                                }
                            }
                        },
                        {
                            "text": "Analyze this document and extract all outcomes mentioned. Remove any bullletpoint/number prefixes for each outcome. Return only a JSON array of strings for the outcomes."
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 2000,
                "temperature": 0.1
            }
        )
        
        ai_response = response['output']['message']['content'][0]['text']
        
        try:
            # Extract JSON from AI response
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1
            outcomes_data = json.loads(ai_response[json_start:json_end])
        except:
            outcomes_data = []
        
        return {
            "total_outcomes": len(outcomes_data),
            "outcomes": outcomes_data
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python extractOutcomes.py <pdf_file_path>")
        sys.exit(1)
    
    with open(sys.argv[1], 'rb') as file:
        pdf_bytes = file.read()
    
    extractor = OutcomeExtractor()
    result = extractor.extract_outcomes(pdf_bytes)
    print(json.dumps(result, indent=2))
