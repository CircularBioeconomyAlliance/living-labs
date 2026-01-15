import boto3
import json
import base64
from pathlib import Path
from typing import Dict, List, Any
from strands import Agent, tool


############ confing ##################
AWS_REGION = "us-west-2"
KB_ID = "MZ6WZLUHSD"  # Outcomes → Indicators Knowledge Base

# Model ID - try Sonnet 4.5, fallback to 3.5 if not available
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Stable in us-west-2

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

########## tools ###########

@tool
def extract_outcomes_from_pdf(pdf_filename: str) -> Dict[str, Any]:
    """Extract indicative outcomes from an agriculture PDF file.
    
    Args:
        pdf_filename: Name of the PDF file (e.g., 'agriculture_case.pdf')
        
    Returns:
        Dictionary with success status and list of outcomes.
    """
    try:
        # Build full path to PDF
        pdf_path = Path.cwd() / pdf_filename
        
        if not pdf_path.exists():
            return {
                "success": False,
                "error": f"PDF file not found: {pdf_filename}",
                "outcomes": []
            }
        
        # Read and encode PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = base64.b64encode(f.read()).decode('utf-8')
        
        # Call Claude with PDF document
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_bytes
                            }
                        },
                        {
                            "type": "text",
                            "text": """Extract ALL indicative outcomes from this agriculture PDF.

An indicative outcome is a measurable result or change that the agriculture project aims to achieve.

Return ONLY a JSON array with this exact format:
[{
  "description": "What this outcome measures or aims to achieve"
}]

Return ONLY the JSON array, no other text or markdown."""
                        }
                    ]
                }],
                "max_tokens": 4096,
                "temperature": 0
            })
        )
        
        # Parse response
        result = json.loads(response['body'].read())
        text = result['content'][0]['text']
        
        # Clean JSON from markdown
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        outcomes = json.loads(text.strip())
        
        return {
            "success": True,
            "outcomes": outcomes,
            "count": len(outcomes)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "outcomes": []
        }


@tool
def find_indicators_for_outcome(description_name: str) -> Dict[str, Any]:
    """Find indicators for a specific outcome description by querying the Knowledge Base.
    
    Args:
        description_name: description of the outcome indicator
        
    Returns:
        Dictionary with success status and list of indicators.
    """
    try:
        # Query Knowledge Base
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={
                "text": f"indicators of outcome: {description_name}"
            },
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 1
                }
            }
        )

        
        return {
            "success": True,
            "outcome": description_name,
            "indicators": response,
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "outcome": description_name,
            "indicators": []
        }

@tool
def find_methods_for_indicator(indicator_name: str) -> Dict[str, Any]:
    """Find measurement methods for a specific indicator by querying KB2.
    
    Args:
        indicator_name: Name of the indicator
        
    Returns:
        Dictionary with success status and list of methods with their metadata (accuracy, cost, ease_of_use).
    """
    try:
        # Query Knowledge Base 2
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={
                "text": f"methods specific for indicator: {indicator_name}"
            },
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 1
                }
            }
        )
        #print(f"HHHHHHHHH indicators of outcome: {description_name}")

        
        return {
            "success": True,
            "indicator": indicator_name,
            "methods": response
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "indicator": indicator_name,
            "methods": []
        }

########## Angent #############

# Create the agent with both tools
agriculture_agent = Agent(
    name="AgricultureOutcomesAgent",
    model=MODEL_ID,
    system_prompt="""You are an expert agriculture advisor that helps extract outcomes, find indicators, and recommend measurement methods.

Your workflow:
1. When given a PDF filename, use extract_outcomes_from_pdf to extract all indicative outcomes

2. For EACH outcome extracted, use find_indicators_for_outcome to find relevant indicators from KB

3. For EACH indicator found, use find_methods_for_indicator to find specific methods (not general) with its accuracy, financial cost and ease of usefrom KB

4. CONVERSATIONAL METHOD SELECTION:
   - Present methods with their 3 key dimensions: accuracy, cost, and ease_of_use
   - Ask the user about their priorities (e.g., "Do you prioritize high accuracy over low cost?")
   - Discuss trade-offs between methods
   - Help the user understand which methods best fit their constraints
   - Only recommend methods after understanding user priorities

5. Present final recommendations clearly showing:
   - Outcome → Indicators → Selected Methods
   - Why each method was selected based on user priorities

Important:
- Extract ALL outcomes, indicators, and methods systematically, except the extra indicators
- Don't skip any steps
- For method selection, ALWAYS engage in conversation to understand user priorities BEFORE making final recommendations
- Be helpful and explain trade-offs clearly (e.g., "Method A has high accuracy but higher cost, while Method B is more affordable but slightly less accurate")
""",
    tools=[extract_outcomes_from_pdf, find_indicators_for_outcome, find_methods_for_indicator]
)




