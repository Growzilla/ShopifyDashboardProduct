"""
AI Code Analyzer Service - OpenAI integration for code analysis.

Provides:
- Bug detection
- Security vulnerability scanning
- Performance optimization suggestions
- Code quality scoring
"""
import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AICodeAnalyzer:
    """
    AI-powered code analysis using OpenAI GPT-4.

    Features:
    - Async execution for non-blocking analysis
    - Structured JSON output for consistent parsing
    - Token tracking for cost management
    - Retry logic for API failures
    """

    ANALYSIS_PROMPT = """You are an expert code reviewer and security analyst. Analyze the following code and provide a comprehensive report.

## Code to Analyze:
```{language}
{code}
```

## Required Analysis:
1. **Bugs**: Identify potential bugs, logic errors, and edge cases
2. **Security Issues**: Find security vulnerabilities (injection, XSS, auth issues, etc.)
3. **Optimizations**: Suggest performance and efficiency improvements
4. **Performance**: Evaluate algorithmic complexity and resource usage

## Output Format (JSON):
{{
    "bugs": [
        {{"severity": "high|medium|low", "line": number, "description": "...", "suggestion": "..."}}
    ],
    "security_issues": [
        {{"severity": "critical|high|medium|low", "type": "...", "line": number, "description": "...", "fix": "..."}}
    ],
    "optimizations": [
        {{"impact": "high|medium|low", "description": "...", "suggestion": "..."}}
    ],
    "performance_suggestions": [
        {{"area": "...", "current": "...", "recommended": "...", "benefit": "..."}}
    ],
    "scores": {{
        "performance": 0-100,
        "security": 0-100,
        "quality": 0-100
    }},
    "overall_grade": "A|B|C|D|F",
    "summary": "Brief overall assessment (2-3 sentences)"
}}

Respond ONLY with valid JSON. No markdown formatting."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def analyze_code(
        self,
        code: str,
        language: str = "python",
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Analyze code using OpenAI GPT-4.

        Args:
            code: Source code to analyze
            language: Programming language
            max_retries: Number of retry attempts

        Returns:
            Analysis results dictionary
        """
        start_time = time.time()
        tokens_used = 0

        prompt = self.ANALYSIS_PROMPT.format(
            language=language,
            code=code[:15000],  # Limit code length to avoid token limits
        )

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a code analysis expert. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,  # Low temperature for consistent analysis
                    max_tokens=4000,
                    response_format={"type": "json_object"},
                )

                tokens_used = response.usage.total_tokens if response.usage else 0
                content = response.choices[0].message.content

                if not content:
                    raise ValueError("Empty response from OpenAI")

                # Parse JSON response
                result = json.loads(content)

                # Add metadata
                result["_metadata"] = {
                    "ai_model": self.model,
                    "tokens_used": tokens_used,
                    "analysis_duration_ms": int((time.time() - start_time) * 1000),
                    "language": language,
                    "code_length": len(code),
                }

                logger.info(
                    "Code analysis completed",
                    tokens=tokens_used,
                    grade=result.get("overall_grade"),
                    duration_ms=result["_metadata"]["analysis_duration_ms"],
                )

                return result

            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse AI response as JSON",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    return self._create_error_result(f"JSON parse error: {e}")

            except Exception as e:
                logger.error(
                    "OpenAI API error",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == max_retries - 1:
                    return self._create_error_result(f"API error: {e}")

                # Exponential backoff
                import asyncio
                await asyncio.sleep(2 ** attempt)

        return self._create_error_result("Max retries exceeded")

    def _create_error_result(self, error: str) -> dict[str, Any]:
        """Create an error result when analysis fails."""
        return {
            "bugs": [],
            "security_issues": [],
            "optimizations": [],
            "performance_suggestions": [],
            "scores": {
                "performance": 0,
                "security": 0,
                "quality": 0,
            },
            "overall_grade": "F",
            "summary": f"Analysis failed: {error}",
            "_metadata": {
                "error": error,
                "ai_model": self.model,
                "tokens_used": 0,
                "analysis_duration_ms": 0,
            },
        }

    async def quick_security_scan(self, code: str, language: str = "python") -> dict[str, Any]:
        """
        Quick security-focused scan for critical vulnerabilities.
        Uses fewer tokens for faster, cheaper analysis.
        """
        prompt = f"""Quickly scan this {language} code for CRITICAL security issues only:

```{language}
{code[:5000]}
```

Return JSON: {{"critical_issues": [{{"type": "...", "description": "...", "line": num}}], "is_safe": true/false}}"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster, cheaper for quick scans
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return json.loads(content) if content else {"critical_issues": [], "is_safe": True}

        except Exception as e:
            logger.error("Quick security scan failed", error=str(e))
            return {"critical_issues": [], "is_safe": True, "error": str(e)}


# Singleton instance
ai_analyzer = AICodeAnalyzer()
