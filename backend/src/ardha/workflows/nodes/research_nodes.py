"""
Research workflow nodes for multi-agent system.

This module defines specialized research nodes that work together
to analyze ideas, conduct market research, competitive analysis,
technical feasibility assessment, and synthesize findings.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from ...core.openrouter import OpenRouterError
from ...core.qdrant import QdrantError
from ..state import WorkflowContext
from ...schemas.workflows.research import ResearchStepResult, ResearchProgressUpdate
from .base import BaseNode

logger = logging.getLogger(__name__)


# Research prompt templates
RESEARCH_PROMPTS = {
    "analyze_idea": """You are an idea analyst. Analyze this product concept and extract key insights:

IDEA: {idea}

Provide structured analysis covering:
1. **Core Concept**: What is the fundamental idea/problem being solved?
2. **Target Audience**: Who are the primary users/customers?
3. **Problem Statement**: What specific pain points does this address?
4. **Value Proposition**: What unique value does this provide?
5. **Key Features**: Essential functionality and capabilities
6. **Success Metrics**: How would success be measured?
7. **Risks & Challenges**: Potential obstacles and concerns
8. **Innovation Level**: How novel is this concept (incremental/transformative)?

Be thorough, objective, and provide specific examples where relevant.""",

    "market_research": """You are a market research analyst. Based on this idea analysis, conduct comprehensive market research:

IDEA ANALYSIS: {idea_analysis}

Provide detailed market assessment covering:
1. **Market Size**: Total Addressable Market (TAM), Serviceable Available Market (SAM), Serviceable Obtainable Market (SOM)
2. **Market Trends**: Current and emerging trends affecting this space
3. **Growth Potential**: Market growth rate and projections
4. **Market Segments**: Key customer segments and their characteristics
5. **Opportunity Windows**: Timing and market readiness
6. **Regulatory Landscape**: Legal and regulatory considerations
7. **Economic Factors**: Economic conditions impacting the market
8. **Market Entry Barriers**: Obstacles to entering this market

Use current market data and provide specific numbers/percentages where possible.""",

    "competitive_analysis": """You are a competitive intelligence analyst. Analyze the competitive landscape for this idea:

IDEA: {idea}
MARKET RESEARCH: {market_research}

Provide comprehensive competitive analysis covering:
1. **Direct Competitors**: Companies offering similar solutions
2. **Indirect Competitors**: Alternative solutions addressing the same problem
3. **Market Leaders**: Dominant players in this space
4. **Competitive Advantages**: What makes each competitor strong/weak
5. **Market Share**: Current market distribution
6. **Pricing Models**: How competitors monetize
7. **Feature Comparison**: Key differentiators and gaps
8. **Strategic Positioning**: Where does this idea fit in the landscape?

Identify specific companies and their strategies. Be objective and data-driven.""",

    "technical_feasibility": """You are a technical feasibility analyst. Assess the technical requirements and feasibility:

IDEA: {idea}
REQUIREMENTS: {requirements}

Provide detailed technical assessment covering:
1. **Technical Complexity**: Overall difficulty level (low/medium/high)
2. **Technology Stack**: Recommended technologies and frameworks
3. **Architecture Requirements**: System design and infrastructure needs
4. **Development Timeline**: Estimated time to build and launch
5. **Resource Requirements**: Team size, skills, and expertise needed
6. **Technical Risks**: Potential technical challenges and mitigations
7. **Scalability Considerations**: How the system will handle growth
8. **Integration Requirements**: Third-party services and APIs needed

Be specific about technologies, provide realistic timelines, and identify potential blockers.""",

    "synthesize": """You are a research synthesizer. Create an executive summary from all research findings:

IDEA ANALYSIS: {idea_analysis}
MARKET RESEARCH: {market_research}
COMPETITIVE ANALYSIS: {competitive_analysis}
TECHNICAL FEASIBILITY: {technical_feasibility}

Create comprehensive executive summary covering:
1. **Executive Summary**: High-level overview and key takeaways
2. **Opportunity Assessment**: Market opportunity and potential
3. **Strategic Recommendations**: Go/No-Go decision and next steps
4. **Risk Assessment**: Major risks and mitigation strategies
5. **Resource Requirements**: What's needed to succeed
6. **Timeline & Milestones**: Recommended development phases
7. **Success Criteria**: How to measure success
8. **Alternative Approaches**: Backup plans and pivots

Be concise, actionable, and provide clear recommendations with supporting evidence."""
}


class ResearchNodeException(Exception):
    """Exception for research node errors."""
    pass


class BaseResearchNode(BaseNode):
    """
    Base class for all research workflow nodes.
    
    Provides common research functionality including
    progress tracking, quality scoring, and result validation.
    """
    
    def __init__(self, node_name: str, model: str):
        """
        Initialize base research node.
        
        Args:
            node_name: Unique name for this node
            model: AI model to use for this node
        """
        super().__init__(node_name)
        self.model = model
    
    async def execute(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute the research node with progress tracking.
        
        Args:
            state: Current workflow state
            context: Workflow execution context
            
        Returns:
            Research step results with metadata
        """
        start_time = time.time()
        
        try:
            # Update progress
            await self._emit_progress_update(
                state, context, "running", 0, 
                f"Starting {self.node_name} analysis..."
            )
            
            # Execute the specific research logic
            result = await self._execute_research_logic(state, context)
            
            # Calculate execution metrics
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Create structured result
            step_result = ResearchStepResult(
                step_name=self.node_name,
                model_used=self.model,
                execution_time_ms=execution_time_ms,
                tokens_used=result.get("tokens_used", 0),
                cost_incurred=result.get("cost", 0.0),
                key_findings=result.get("key_findings", []),
                data_sources=result.get("data_sources", []),
                confidence_score=result.get("confidence_score", 0.0),
                completeness_score=result.get("completeness_score", 0.0),
                accuracy_score=result.get("accuracy_score", 0.0),
                raw_content=result.get("raw_content", ""),
                structured_data=result.get("structured_data", {}),
            )
            
            # Update progress with completion
            await self._emit_progress_update(
                state, context, "completed", 100,
                f"Completed {self.node_name} analysis",
                step_result=step_result
            )
            
            self.logger.info(f"Research node {self.node_name} completed in {execution_time_ms}ms")
            return step_result.model_dump()
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Emit error progress update
            await self._emit_progress_update(
                state, context, "failed", 0,
                f"Failed {self.node_name} analysis: {str(e)}",
                error_message=str(e)
            )
            
            self.logger.error(f"Research node {self.node_name} failed after {execution_time_ms}ms: {e}")
            raise ResearchNodeException(f"{self.node_name} failed: {str(e)}") from e
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Execute the specific research logic.
        
        Must be implemented by subclasses.
        
        Args:
            state: Current workflow state
            context: Workflow execution context
            
        Returns:
            Research results with metadata
        """
        raise NotImplementedError("Subclasses must implement _execute_research_logic")
    
    async def _emit_progress_update(
        self,
        state,
        context: WorkflowContext,
        step_status: str,
        progress_percentage: int,
        message: str,
        step_result: Optional[ResearchStepResult] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Emit progress update for streaming.
        
        Args:
            state: Current workflow state
            context: Workflow execution context
            step_status: Status of the step
            progress_percentage: Progress percentage
            message: Status message
            step_result: Optional step result
            error_message: Optional error message
        """
        try:
            # Update state progress
            if hasattr(state, 'update_progress'):
                state.update_progress(self.node_name, progress_percentage)
            
            # Create progress update
            progress_update = ResearchProgressUpdate(
                workflow_id=state.workflow_id,
                execution_id=state.execution_id,
                current_step=self.node_name,
                step_status=step_status,
                progress_percentage=progress_percentage,
                step_result_preview=step_result.raw_content[:200] if step_result else None,
                key_findings_preview=step_result.key_findings[:3] if step_result else [],
                step_confidence=step_result.confidence_score if step_result else None,
                quality_score=step_result.completeness_score if step_result else None,
                error_message=error_message,
                timestamp=state._get_timestamp(),
            )
            
            # Call progress callback if available
            if context.progress_callback:
                await context.progress_callback(progress_update)
                
        except Exception as e:
            self.logger.warning(f"Failed to emit progress update: {e}")


class AnalyzeIdeaNode(BaseResearchNode):
    """Node for analyzing the core idea and extracting key concepts."""
    
    def __init__(self):
        super().__init__("analyze_idea", "z-ai/glm-4.6")
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Execute idea analysis research."""
        idea = state.idea if hasattr(state, 'idea') else state.initial_request
        
        # Get relevant context
        context_items = await self._get_relevant_context(
            f"idea analysis {idea}", context, state, limit=5
        )
        
        # Prepare prompt
        prompt = RESEARCH_PROMPTS["analyze_idea"].format(idea=idea)
        
        messages = [
            {"role": "system", "content": "You are an expert idea analyst. Be thorough and structured."},
            {"role": "user", "content": prompt}
        ]
        
        # Add context if available
        if context_items:
            context_text = "\n".join([
                f"- {item['text']}" for item in context_items[:3]
            ])
            messages.insert(1, {
                "role": "system",
                "content": f"Relevant context from similar ideas:\n{context_text}"
            })
        
        # Call AI
        response = await self._call_ai(
            messages=messages,
            model=self.model,
            context=context,
            state=state,
            temperature=0.3,
            max_tokens=2000,
        )
        
        # Extract key findings (simple keyword extraction for now)
        key_findings = self._extract_key_findings(response)
        
        # Update state with sources found
        if hasattr(state, 'sources_found'):
            state.sources_found += len(context_items)
        
        return {
            "raw_content": response,
            "key_findings": key_findings,
            "data_sources": [f"Context item {i+1}" for i in range(len(context_items))],
            "confidence_score": 0.85,  # High confidence for idea analysis
            "completeness_score": 0.9,
            "accuracy_score": 0.8,
            "structured_data": {
                "idea": idea,
                "analysis_length": len(response),
                "context_items_used": len(context_items),
            }
        }
    
    def _extract_key_findings(self, content: str) -> List[str]:
        """Extract key findings from AI response."""
        # Simple extraction based on markdown headers
        findings = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                # Extract bolded headers as key findings
                finding = line.replace('**', '').strip()
                if len(finding) > 5:  # Filter out very short findings
                    findings.append(finding)
        
        return findings[:5]  # Return top 5 findings


class MarketResearchNode(BaseResearchNode):
    """Node for conducting market research and analysis."""
    
    def __init__(self):
        super().__init__("market_research", "anthropic/claude-sonnet-4.5")
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Execute market research analysis."""
        # Get idea analysis from previous step
        idea_analysis = ""
        if hasattr(state, 'idea_analysis') and state.idea_analysis:
            idea_analysis = state.idea_analysis.get("raw_content", "")
        elif "analyze_idea" in state.results:
            idea_analysis = state.results["analyze_idea"].get("raw_content", "")
        
        if not idea_analysis:
            idea_analysis = state.idea if hasattr(state, 'idea') else state.initial_request
        
        # Get market context
        context_items = await self._get_relevant_context(
            f"market research {idea_analysis}", context, state, limit=8
        )
        
        # Prepare prompt
        prompt = RESEARCH_PROMPTS["market_research"].format(idea_analysis=idea_analysis)
        
        messages = [
            {"role": "system", "content": "You are an expert market research analyst. Use current market data and be specific with numbers."},
            {"role": "user", "content": prompt}
        ]
        
        # Add market context if available
        if context_items:
            context_text = "\n".join([
                f"- {item['text']}" for item in context_items[:5]
            ])
            messages.insert(1, {
                "role": "system",
                "content": f"Relevant market data and research:\n{context_text}"
            })
        
        # Call AI
        response = await self._call_ai(
            messages=messages,
            model=self.model,
            context=context,
            state=state,
            temperature=0.2,  # Lower temperature for factual market data
            max_tokens=3000,
        )
        
        # Extract key findings
        key_findings = self._extract_market_findings(response)
        
        # Update state
        if hasattr(state, 'sources_found'):
            state.sources_found += len(context_items)
        if hasattr(state, 'market_data_quality'):
            state.market_data_quality = 0.85
        
        return {
            "raw_content": response,
            "key_findings": key_findings,
            "data_sources": [f"Market data source {i+1}" for i in range(len(context_items))],
            "confidence_score": 0.8,
            "completeness_score": 0.85,
            "accuracy_score": 0.75,
            "structured_data": {
                "market_segments": self._extract_market_segments(response),
                "growth_potential": "high" if "growth" in response.lower() else "medium",
                "context_items_used": len(context_items),
            }
        }
    
    def _extract_market_findings(self, content: str) -> List[str]:
        """Extract market-specific key findings."""
        findings = []
        market_keywords = ["market size", "growth", "revenue", "opportunity", "trends"]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for keyword in market_keywords:
                if keyword in line.lower() and len(line) > 10:
                    findings.append(line)
                    break
        
        return findings[:5]
    
    def _extract_market_segments(self, content: str) -> List[str]:
        """Extract market segments from content."""
        segments = []
        if "segments" in content.lower():
            lines = content.split('\n')
            for line in lines:
                if "segment" in line.lower() and ":" in line:
                    segment = line.split(":")[-1].strip()
                    if segment and len(segment) > 3:
                        segments.append(segment)
        
        return segments[:3]


class CompetitiveAnalysisNode(BaseResearchNode):
    """Node for conducting competitive analysis."""
    
    def __init__(self):
        super().__init__("competitive_analysis", "anthropic/claude-sonnet-4.5")
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Execute competitive analysis."""
        # Get idea and market research
        idea = state.idea if hasattr(state, 'idea') else state.initial_request
        market_research = ""
        
        if hasattr(state, 'market_research') and state.market_research:
            market_research = state.market_research.get("raw_content", "")
        elif "market_research" in state.results:
            market_research = state.results["market_research"].get("raw_content", "")
        
        # Get competitive context
        context_items = await self._get_relevant_context(
            f"competitive analysis {idea}", context, state, limit=8
        )
        
        # Prepare prompt
        prompt = RESEARCH_PROMPTS["competitive_analysis"].format(
            idea=idea,
            market_research=market_research[:1000] if market_research else "No market research available"
        )
        
        messages = [
            {"role": "system", "content": "You are a competitive intelligence analyst. Be objective and data-driven."},
            {"role": "user", "content": prompt}
        ]
        
        # Add competitive context
        if context_items:
            context_text = "\n".join([
                f"- {item['text']}" for item in context_items[:5]
            ])
            messages.insert(1, {
                "role": "system",
                "content": f"Relevant competitive intelligence:\n{context_text}"
            })
        
        # Call AI
        response = await self._call_ai(
            messages=messages,
            model=self.model,
            context=context,
            state=state,
            temperature=0.3,
            max_tokens=3000,
        )
        
        # Extract key findings
        key_findings = self._extract_competitor_findings(response)
        
        # Update state
        if hasattr(state, 'sources_found'):
            state.sources_found += len(context_items)
        if hasattr(state, 'competitor_coverage'):
            state.competitor_coverage = 0.8
        
        return {
            "raw_content": response,
            "key_findings": key_findings,
            "data_sources": [f"Competitor data source {i+1}" for i in range(len(context_items))],
            "confidence_score": 0.75,
            "completeness_score": 0.8,
            "accuracy_score": 0.7,
            "structured_data": {
                "competitors_identified": self._extract_competitors(response),
                "market_position": "emerging" if "new" in response.lower() else "established",
                "context_items_used": len(context_items),
            }
        }
    
    def _extract_competitor_findings(self, content: str) -> List[str]:
        """Extract competitor-specific findings."""
        findings = []
        competitor_keywords = ["competitor", "market share", "advantage", "weakness"]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for keyword in competitor_keywords:
                if keyword in line.lower() and len(line) > 10:
                    findings.append(line)
                    break
        
        return findings[:5]
    
    def _extract_competitors(self, content: str) -> List[str]:
        """Extract competitor names from content."""
        competitors = []
        # Simple extraction - look for company names in competitive analysis
        # This could be enhanced with NLP in the future
        common_companies = ["google", "microsoft", "apple", "amazon", "meta", "tesla"]
        
        for company in common_companies:
            if company in content.lower():
                competitors.append(company.title())
        
        return competitors[:5]


class TechnicalFeasibilityNode(BaseResearchNode):
    """Node for assessing technical feasibility."""
    
    def __init__(self):
        super().__init__("technical_feasibility", "z-ai/glm-4.6")
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Execute technical feasibility assessment."""
        # Get idea and requirements
        idea = state.idea if hasattr(state, 'idea') else state.initial_request
        requirements = ""
        
        # Compile requirements from previous steps
        if hasattr(state, 'idea_analysis') and state.idea_analysis:
            requirements += state.idea_analysis.get("raw_content", "") + "\n"
        if hasattr(state, 'market_research') and state.market_research:
            requirements += state.market_research.get("raw_content", "") + "\n"
        if hasattr(state, 'competitive_analysis') and state.competitive_analysis:
            requirements += state.competitive_analysis.get("raw_content", "")
        
        # Get technical context
        context_items = await self._get_relevant_context(
            f"technical feasibility {idea}", context, state, limit=6
        )
        
        # Prepare prompt
        prompt = RESEARCH_PROMPTS["technical_feasibility"].format(
            idea=idea,
            requirements=requirements[:1500] if requirements else idea
        )
        
        messages = [
            {"role": "system", "content": "You are a technical feasibility analyst. Be realistic and specific about technical requirements."},
            {"role": "user", "content": prompt}
        ]
        
        # Add technical context
        if context_items:
            context_text = "\n".join([
                f"- {item['text']}" for item in context_items[:3]
            ])
            messages.insert(1, {
                "role": "system",
                "content": f"Relevant technical implementations and patterns:\n{context_text}"
            })
        
        # Call AI
        response = await self._call_ai(
            messages=messages,
            model=self.model,
            context=context,
            state=state,
            temperature=0.2,  # Lower temperature for technical analysis
            max_tokens=2500,
        )
        
        # Extract key findings
        key_findings = self._extract_technical_findings(response)
        
        # Update state
        if hasattr(state, 'sources_found'):
            state.sources_found += len(context_items)
        if hasattr(state, 'technical_detail_level'):
            state.technical_detail_level = 0.85
        
        return {
            "raw_content": response,
            "key_findings": key_findings,
            "data_sources": [f"Technical reference {i+1}" for i in range(len(context_items))],
            "confidence_score": 0.8,
            "completeness_score": 0.85,
            "accuracy_score": 0.75,
            "structured_data": {
                "complexity_level": self._extract_complexity(response),
                "technologies_recommended": self._extract_technologies(response),
                "context_items_used": len(context_items),
            }
        }
    
    def _extract_technical_findings(self, content: str) -> List[str]:
        """Extract technical findings."""
        findings = []
        tech_keywords = ["complexity", "technology", "architecture", "development", "timeline"]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for keyword in tech_keywords:
                if keyword in line.lower() and len(line) > 10:
                    findings.append(line)
                    break
        
        return findings[:5]
    
    def _extract_complexity(self, content: str) -> str:
        """Extract complexity level from content."""
        if "high complexity" in content.lower() or "very complex" in content.lower():
            return "high"
        elif "low complexity" in content.lower() or "simple" in content.lower():
            return "low"
        else:
            return "medium"
    
    def _extract_technologies(self, content: str) -> List[str]:
        """Extract recommended technologies."""
        technologies = []
        tech_stack = ["python", "javascript", "react", "node", "aws", "docker", "kubernetes", "postgresql"]
        
        for tech in tech_stack:
            if tech in content.lower():
                technologies.append(tech)
        
        return technologies[:5]


class SynthesizeResearchNode(BaseResearchNode):
    """Node for synthesizing all research findings into executive summary."""
    
    def __init__(self):
        super().__init__("synthesize_research", "anthropic/claude-sonnet-4.5")
    
    async def _execute_research_logic(
        self,
        state,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """Execute research synthesis."""
        # Gather all previous research
        idea_analysis = ""
        market_research = ""
        competitive_analysis = ""
        technical_feasibility = ""
        
        # Get results from state
        if hasattr(state, 'idea_analysis') and state.idea_analysis:
            idea_analysis = state.idea_analysis.get("raw_content", "")
        elif "analyze_idea" in state.results:
            idea_analysis = state.results["analyze_idea"].get("raw_content", "")
            
        if hasattr(state, 'market_research') and state.market_research:
            market_research = state.market_research.get("raw_content", "")
        elif "market_research" in state.results:
            market_research = state.results["market_research"].get("raw_content", "")
            
        if hasattr(state, 'competitive_analysis') and state.competitive_analysis:
            competitive_analysis = state.competitive_analysis.get("raw_content", "")
        elif "competitive_analysis" in state.results:
            competitive_analysis = state.results["competitive_analysis"].get("raw_content", "")
            
        if hasattr(state, 'technical_feasibility') and state.technical_feasibility:
            technical_feasibility = state.technical_feasibility.get("raw_content", "")
        elif "technical_feasibility" in state.results:
            technical_feasibility = state.results["technical_feasibility"].get("raw_content", "")
        
        # Prepare synthesis prompt
        prompt = RESEARCH_PROMPTS["synthesize"].format(
            idea_analysis=idea_analysis[:800] if idea_analysis else "No idea analysis available",
            market_research=market_research[:800] if market_research else "No market research available",
            competitive_analysis=competitive_analysis[:800] if competitive_analysis else "No competitive analysis available",
            technical_feasibility=technical_feasibility[:800] if technical_feasibility else "No technical feasibility available"
        )
        
        messages = [
            {"role": "system", "content": "You are an expert research synthesizer. Create actionable executive summary with clear recommendations."},
            {"role": "user", "content": prompt}
        ]
        
        # Call AI
        response = await self._call_ai(
            messages=messages,
            model=self.model,
            context=context,
            state=state,
            temperature=0.4,  # Balanced for synthesis
            max_tokens=3000,
        )
        
        # Extract key findings
        key_findings = self._extract_synthesis_findings(response)
        
        # Calculate overall research confidence
        if hasattr(state, 'calculate_research_confidence'):
            overall_confidence = state.calculate_research_confidence()
        else:
            overall_confidence = 0.8
        
        return {
            "raw_content": response,
            "key_findings": key_findings,
            "data_sources": ["Idea Analysis", "Market Research", "Competitive Analysis", "Technical Feasibility"],
            "confidence_score": overall_confidence,
            "completeness_score": 0.9,
            "accuracy_score": 0.8,
            "structured_data": {
                "recommendation": self._extract_recommendation(response),
                "go_no_go": self._extract_go_no_go(response),
                "next_steps": self._extract_next_steps(response),
                "research_completeness": 1.0,  # Synthesis marks completion
            }
        }
    
    def _extract_synthesis_findings(self, content: str) -> List[str]:
        """Extract synthesis findings."""
        findings = []
        synthesis_keywords = ["recommendation", "opportunity", "risk", "strategy", "conclusion"]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for keyword in synthesis_keywords:
                if keyword in line.lower() and len(line) > 10:
                    findings.append(line)
                    break
        
        return findings[:5]
    
    def _extract_recommendation(self, content: str) -> str:
        """Extract main recommendation."""
        if "recommend" in content.lower():
            lines = content.split('\n')
            for line in lines:
                if "recommend" in line.lower():
                    return line.strip()
        return "Proceed with caution - further validation needed"
    
    def _extract_go_no_go(self, content: str) -> str:
        """Extract Go/No-Go decision."""
        if "go" in content.lower() and "no-go" not in content.lower():
            return "GO"
        elif "no-go" in content.lower() or "no go" in content.lower():
            return "NO-GO"
        else:
            return "CONDITIONAL"
    
    def _extract_next_steps(self, content: str) -> List[str]:
        """Extract next steps from synthesis."""
        steps = []
        if "next steps" in content.lower() or "recommendations" in content.lower():
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    step = line.strip().lstrip('-*').strip()
                    if len(step) > 5:
                        steps.append(step)
        
        return steps[:3]