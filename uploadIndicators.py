import boto3
import json
import base64
import sys

class ImageDataExtractor:
    def __init__(self, region_name='us-east-1'):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
    
    def extract_data_from_image(self, image_bytes):
        prompt = "Extract all data points from this image and return them as a JSON array. Just extract the numbers and not the units. Each data point should be a JSON object."
        
        response = self.bedrock_client.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(image_bytes).decode()}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            })
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python uploadIndicators.py <image_path>")
        sys.exit(1)
    
    with open(sys.argv[1], 'rb') as f:
        image_bytes = f.read()
    
    extractor = ImageDataExtractor()
    result = extractor.extract_data_from_image(image_bytes)
    print(result)
