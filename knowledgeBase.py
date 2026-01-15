import boto3
import json
from botocore.exceptions import ClientError

class BedrockKnowledgeBase:
    def __init__(self, region_name='us-west-2'):
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region_name)
        self.bedrock_runtime_client = boto3.client('bedrock-agent-runtime', region_name=region_name)

    def query_with_generation(self, knowledge_base_id, query, model_arn=None, conversation=None):
        """Query KB and generate response"""
        try:
            request_config = {
                'input': {'text': query},
                'retrieveAndGenerateConfiguration': {
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': knowledge_base_id
                    }
                }
            }

            if model_arn:
                request_config['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['modelArn'] = model_arn
            
            if conversation:
                if isinstance(conversation, str):
                    conversation = json.loads(conversation)
                prompt = "Previous conversation:\n"
                for msg in conversation:
                    prompt += f"{msg['role']}: {msg['content']}\n"
                prompt += "\n$search_results$\n\n$output_format_instructions$"
                request_config['retrieveAndGenerateConfiguration']['knowledgeBaseConfiguration']['generationConfiguration'] = {
                    'promptTemplate': {
                        'textPromptTemplate': prompt
                    }
                }

            response = self.bedrock_runtime_client.retrieve_and_generate(**request_config)
            return response

        except ClientError as e:
            print(f"Error: {e}")
            raise

# Usage
kb = BedrockKnowledgeBase()
knowledge_base_id = "9EUJJVMIU3"  # Your KB ID

# Example conversation history
conversation = json.dumps([
    {"role": "user", "content": "What are the key principles for monitoring?"},
    {"role": "assistant", "content": "The key principles include establishing clear objectives and selecting appropriate indicators."}
])

# Query your knowledge base with conversation history
response = kb.query_with_generation(
    knowledge_base_id=knowledge_base_id,
    # query="What are the indicators for the first objective? Return the indicators in a bulletpoint list.",
    query="Summarise our existing conversation and then tell me what the most expensive indicator collection method is.",
    model_arn="arn:aws:bedrock:us-west-2:864626407820:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    conversation=conversation
)

print("Response:", response['output']['text'])
if 'citations' in response:
    print("Sources:", len(response['citations']), "citations found")
