"""
NVIDIA Nemotron AI Investigation Service via Nebius Token Factory

Provides AI-powered ANPR event analysis using NVIDIA Nemotron through
the Nebius Token Factory OpenAI-compatible API.

This service acts as an additional intelligence layer for ANPR investigation,
providing incident summaries, pattern detection, and review recommendations.

IMPORTANT:
- Does NOT replace vehicle detection (YOLOv8)
- Does NOT replace plate detection
- Does NOT replace OCR (EasyOCR)
- Does NOT make criminality judgments
- Does NOT override security rules
"""
import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from openai import AsyncOpenAI, OpenAIError, APIError, APIConnectionError, RateLimitError, AuthenticationError

logger = logging.getLogger(__name__)


class NebiusNemotronService:
    """
    Nebius Token Factory NVIDIA Nemotron integration service.
    
    Provides AI-powered ANPR event investigation assistance.
    """
    
    def __init__(self):
        """Initialize the Nebius Nemotron service."""
        self.api_key = os.getenv("NEBIUS_API_KEY")
        self.model = os.getenv("NEBIUS_MODEL", "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF")
        self.base_url = "https://api.tokenfactory.nebius.com/v1/"
        self.timeout = 30.0  # 30 second timeout
        
        # Initialize client if credentials available
        self.client = None
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"✅ Nebius Nemotron service initialized with model: {self.model}")
        else:
            logger.warning("⚠️  NEBIUS_API_KEY not configured. AI investigation features disabled.")
    
    def is_available(self) -> bool:
        """Check if the service is available (credentials configured)."""
        return self.client is not None
    
    async def verify_connection(self) -> Dict[str, Any]:
        """
        Verify connection to Nebius API and list available models.
        
        Returns:
            Dict with connection status and available models
        """
        if not self.is_available():
            return {
                "available": False,
                "error": "NEBIUS_API_KEY not configured",
                "models": []
            }
        
        try:
            # List available models
            models = await self.client.models.list()
            model_ids = [model.id for model in models.data]
            
            # Check if configured model is available
            model_available = self.model in model_ids
            
            return {
                "available": True,
                "base_url": self.base_url,
                "configured_model": self.model,
                "model_available": model_available,
                "available_models": model_ids[:5],  # First 5 models
                "total_models": len(model_ids)
            }
        except AuthenticationError as e:
            logger.error(f"Nebius authentication failed: {e}")
            return {
                "available": False,
                "error": "Authentication failed - invalid API key",
                "models": []
            }
        except APIConnectionError as e:
            logger.error(f"Nebius connection failed: {e}")
            return {
                "available": False,
                "error": "Connection failed - check network",
                "models": []
            }
        except Exception as e:
            logger.error(f"Nebius verification failed: {e}")
            return {
                "available": False,
                "error": str(e),
                "models": []
            }
    
    def _build_investigation_prompt(self, event_data: Dict[str, Any]) -> str:
        """
        Build the investigation prompt for Nemotron.
        
        Args:
            event_data: Structured ANPR event data
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an AI assistant for an Automatic Number Plate Recognition (ANPR) system called EagleVision.

Your role is to analyze ANPR detection events and provide investigative insights to help human operators review incidents efficiently.

**IMPORTANT LIMITATIONS:**
- You MUST NOT make criminality judgments
- You MUST NOT declare vehicles suspicious without evidence
- You MUST NOT recommend law enforcement actions
- You MUST clearly state uncertainty and confidence levels
- You provide analysis to assist human review, not replace it

**ANPR EVENT DATA:**

Event ID: {event_data.get('event_id', 'N/A')}
Timestamp: {event_data.get('timestamp', 'N/A')}
Camera ID: {event_data.get('camera_id', 'Unknown')}

Vehicle Detection:
- Class: {event_data.get('vehicle_class', 'Unknown')}
- Confidence: {event_data.get('vehicle_confidence', 'N/A')}%

Plate Detection:
- Method: {event_data.get('plate_method', 'N/A')}
- Detection Confidence: {event_data.get('plate_confidence', 'N/A')}%

OCR Result:
- Text: {event_data.get('ocr_text', 'N/A')}
- OCR Confidence: {event_data.get('ocr_confidence', 'N/A')}%
- Engine: {event_data.get('ocr_engine', 'N/A')}
- Needs Review: {event_data.get('needs_review', False)}
- Review Reason: {event_data.get('review_reason', 'N/A')}

Additional Context:
{json.dumps(event_data.get('context', {}), indent=2)}

**YOUR TASK:**

Provide a structured analysis in the following format:

1. **Incident Summary** (2-3 sentences)
   - Brief factual description of the detection event

2. **Detection Quality Assessment**
   - Vehicle detection quality and confidence
   - Plate detection quality and confidence
   - OCR result quality and confidence

3. **Observed Patterns** (if any)
   - Any notable patterns in the data
   - Comparison with typical detection quality

4. **OCR Uncertainty Analysis**
   - Why this OCR result might need review
   - Possible sources of error or ambiguity

5. **Recommended Actions**
   - Specific evidence to review (e.g., examine frame image)
   - Priority level (Low/Medium/High) with justification
   - What a human reviewer should focus on

6. **Confidence & Limitations**
   - Your confidence level in this analysis (Low/Medium/High)
   - Explicit uncertainties and what you cannot determine
   - What additional information would improve the analysis

Provide your analysis now:"""
        
        return prompt
    
    async def analyze_anpr_event(
        self,
        event_data: Dict[str, Any],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze an ANPR event using NVIDIA Nemotron.
        
        Args:
            event_data: Structured ANPR event data containing:
                - event_id: Event identifier
                - timestamp: Detection timestamp
                - camera_id: Camera identifier
                - vehicle_class: Vehicle type
                - vehicle_confidence: Vehicle detection confidence
                - plate_method: Plate detection method
                - plate_confidence: Plate detection confidence
                - ocr_text: OCR result text
                - ocr_confidence: OCR confidence score
                - ocr_engine: OCR engine used
                - needs_review: Whether review is needed
                - review_reason: Reason for review
                - context: Additional contextual information
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (0.0-1.0)
        
        Returns:
            Dict containing:
                - success: Whether analysis succeeded
                - analysis: AI-generated analysis text
                - model: Model used
                - timestamp: Analysis timestamp
                - error: Error message if failed
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Nebius Nemotron service not configured. Set NEBIUS_API_KEY environment variable.",
                "analysis": None,
                "model": None,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Build prompt
            prompt = self._build_investigation_prompt(event_data)
            
            # Call Nemotron API
            logger.info(f"🔍 Analyzing ANPR event {event_data.get('event_id')} with Nemotron...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant for ANPR investigation. Provide factual, helpful analysis without making judgments about criminality."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Extract analysis
            analysis_text = response.choices[0].message.content
            
            result = {
                "success": True,
                "analysis": analysis_text,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "timestamp": datetime.utcnow().isoformat(),
                "event_id": event_data.get('event_id'),
                "error": None
            }
            
            logger.info(f"✅ Analysis completed: {response.usage.total_tokens} tokens")
            return result
        
        except AuthenticationError as e:
            logger.error(f"Nebius authentication failed: {e}")
            return {
                "success": False,
                "error": "Authentication failed. Check NEBIUS_API_KEY.",
                "analysis": None,
                "model": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except RateLimitError as e:
            logger.error(f"Nebius rate limit exceeded: {e}")
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "analysis": None,
                "model": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except APIConnectionError as e:
            logger.error(f"Nebius connection failed: {e}")
            return {
                "success": False,
                "error": "Connection failed. Check network connectivity.",
                "analysis": None,
                "model": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except APIError as e:
            logger.error(f"Nebius API error: {e}")
            return {
                "success": False,
                "error": f"API error: {str(e)}",
                "analysis": None,
                "model": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Unexpected error in Nemotron analysis: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "analysis": None,
                "model": self.model,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def batch_analyze_events(
        self,
        events: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple ANPR events concurrently.
        
        Args:
            events: List of event data dicts
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of analysis results
        """
        if not self.is_available():
            return [{
                "success": False,
                "error": "Service not configured",
                "event_id": event.get('event_id')
            } for event in events]
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_limit(event):
            async with semaphore:
                return await self.analyze_anpr_event(event)
        
        # Run analyses concurrently
        results = await asyncio.gather(
            *[analyze_with_limit(event) for event in events],
            return_exceptions=True
        )
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "event_id": events[i].get('event_id')
                })
            else:
                processed_results.append(result)
        
        return processed_results


# Global service instance
_nemotron_service = None


def get_nemotron_service() -> NebiusNemotronService:
    """
    Get the global Nemotron service instance.
    
    Returns:
        NebiusNemotronService instance
    """
    global _nemotron_service
    if _nemotron_service is None:
        _nemotron_service = NebiusNemotronService()
    return _nemotron_service
