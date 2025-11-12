"""
PRD (Product Requirements Document) workflow nodes.

This module implements the specialized AI nodes for converting
research into structured requirements and generating PRD documents.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseNode
from ...schemas.workflows.prd import PRDState, PRDStepResult
from ...workflows.state import WorkflowState, WorkflowContext


class PRDBaseNode(BaseNode):
    """Base class for PRD workflow nodes with name property compatibility."""
    
    @property
    def name(self) -> str:
        """Get node name for compatibility."""
        return self.node_name

logger = logging.getLogger(__name__)


class PRDNodeException(Exception):
    """Base exception for PRD workflow nodes."""
    pass


class ExtractRequirementsNode(PRDBaseNode):
    """
    Node for extracting functional and non-functional requirements from research.
    
    Takes research summary and extracts structured requirements that will
    form the foundation of the PRD document.
    """
    
    def __init__(self):
        super().__init__("extract_requirements")
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Extract requirements from research summary.
        
        Args:
            state: Current PRD workflow state
            context: Workflow execution context
            
        Returns:
            Extracted requirements structure
        """
        try:
            # Cast to PRDState to access PRD-specific attributes
            prd_state = state if isinstance(state, PRDState) else PRDState(**state.model_dump())
            
            self.logger.info("Extracting requirements from research summary")
            
            # Prepare system prompt for requirements extraction
            system_prompt = """You are a expert product analyst and requirements engineer. 

Your task is to extract comprehensive requirements from the provided research summary.

Categorize requirements into:
1. Functional Requirements - What the system must do
2. Non-Functional Requirements - How the system must perform (security, performance, usability, etc.)
3. Business Requirements - Business goals and constraints
4. Technical Requirements - Technical specifications and constraints

For each requirement, provide:
- Unique identifier (REQ-001, REQ-002, etc.)
- Clear, concise description
- Priority (High, Medium, Low)
- Category (Functional, Non-Functional, Business, Technical)
- Acceptance criteria or measurable success criteria

Format your response as structured JSON with the following schema:
{
  "functional_requirements": [
    {
      "id": "REQ-F-001",
      "description": "Clear description of what the system must do",
      "priority": "High|Medium|Low",
      "acceptance_criteria": "Measurable criteria for completion"
    }
  ],
  "non_functional_requirements": [
    {
      "id": "REQ-NF-001", 
      "description": "Performance, security, usability, etc. requirements",
      "priority": "High|Medium|Low",
      "category": "Performance|Security|Usability|Reliability|Scalability",
      "metrics": "Specific measurable metrics"
    }
  ],
  "business_requirements": [
    {
      "id": "REQ-B-001",
      "description": "Business goals and constraints",
      "priority": "High|Medium|Low",
      "success_criteria": "Business success metrics"
    }
  ],
  "technical_requirements": [
    {
      "id": "REQ-T-001",
      "description": "Technical specifications and constraints",
      "priority": "High|Medium|Low",
      "constraints": "Technical limitations or requirements"
    }
  ],
  "requirements_summary": {
    "total_requirements": 0,
    "by_priority": {"high": 0, "medium": 0, "low": 0},
    "by_category": {"functional": 0, "non_functional": 0, "business": 0, "technical": 0}
  }
}

Focus on clarity, completeness, and measurability. Each requirement should be testable and unambiguous."""
            
            # Prepare user prompt with research summary
            user_prompt = f"""Extract comprehensive requirements from the following research summary:

{json.dumps(prd_state.research_summary, indent=2)}

Please analyze the research and extract all relevant requirements following the specified JSON schema. Ensure requirements are:
- Clear and unambiguous
- Testable and measurable
- Properly prioritized
- Complete and comprehensive

Return only valid JSON that can be parsed."""
            
            # Make AI call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model = context.settings.get("extract_requirements_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.3)
            
            # Parse and validate the response
            try:
                requirements_data = json.loads(response)
                
                # Validate structure
                required_sections = ["functional_requirements", "non_functional_requirements", 
                                  "business_requirements", "technical_requirements", "requirements_summary"]
                
                for section in required_sections:
                    if section not in requirements_data:
                        raise ValueError(f"Missing required section: {section}")
                
                # Calculate completeness score
                total_requirements = requirements_data["requirements_summary"]["total_requirements"]
                expected_minimum = 5  # Minimum requirements for a decent PRD
                completeness_score = min(1.0, total_requirements / max(expected_minimum, total_requirements))
                
                # Store result
                result = {
                    "requirements": requirements_data,
                    "total_requirements": total_requirements,
                    "completeness_score": completeness_score,
                    "extraction_confidence": 0.85 if total_requirements >= expected_minimum else 0.65,
                    "model_used": model,
                }
                
                # Update state quality metrics
                prd_state.requirements_completeness = completeness_score
                
                # Update the original state with PRD-specific attributes
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump()
                    state_dict.update(prd_state.model_dump())
                    for key, value in state_dict.items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                
                self.logger.info(f"Successfully extracted {total_requirements} requirements")
                return result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse requirements JSON: {e}")
                raise PRDNodeException(f"Invalid JSON response from AI: {e}")
            
        except Exception as e:
            self.logger.error(f"Requirements extraction failed: {e}")
            raise PRDNodeException(f"Requirements extraction failed: {str(e)}") from e


class DefineFeaturesNode(PRDBaseNode):
    """
    Node for defining and prioritizing features based on requirements.
    
    Takes extracted requirements and breaks them down into a prioritized
    feature list using MoSCoW prioritization method.
    """
    
    def __init__(self):
        super().__init__("define_features")
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Define and prioritize features from requirements.
        
        Args:
            state: Current PRD workflow state
            context: Workflow execution context
            
        Returns:
            Prioritized feature roadmap
        """
        try:
            # Cast to PRDState to access PRD-specific attributes
            prd_state = state if isinstance(state, PRDState) else PRDState(**state.model_dump())
            
            self.logger.info("Defining and prioritizing features from requirements")
            
            # Prepare system prompt for feature definition
            system_prompt = """You are a expert product manager and solution architect.

Your task is to convert the extracted requirements into a prioritized feature roadmap using MoSCoW prioritization:

MoSCoW Categories:
- MUST HAVE (M): Critical features required for MVP/launch
- SHOULD HAVE (S): Important features that add significant value
- COULD HAVE (C): Nice-to-have features if time/resources permit
- WON'T HAVE (W): Features explicitly excluded from current scope

For each feature, provide:
- Unique identifier (FEAT-001, FEAT-002, etc.)
- Clear feature name and description
- MoSCoW priority (M/S/C/W)
- User stories or use cases
- Estimated complexity (Simple/Medium/Complex)
- Dependencies on other features
- Acceptance criteria
- Related requirements IDs

Format your response as structured JSON:
{
  "features": [
    {
      "id": "FEAT-001",
      "name": "Clear feature name",
      "description": "Detailed description of what the feature does",
      "priority": "M|S|C|W",
      "user_stories": [
        "As a [user type], I want [action] so that [benefit]"
      ],
      "complexity": "Simple|Medium|Complex",
      "dependencies": ["FEAT-002", "FEAT-003"],
      "acceptance_criteria": ["Criteria 1", "Criteria 2"],
      "related_requirements": ["REQ-F-001", "REQ-NF-002"],
      "estimated_effort": "Story points or time estimate"
    }
  ],
  "feature_roadmap": {
    "must_have_features": [],
    "should_have_features": [],
    "could_have_features": [],
    "wont_have_features": [],
    "total_features": 0,
    "priority_distribution": {"M": 0, "S": 0, "C": 0, "W": 0}
  },
  "release_phases": [
    {
      "phase": "Phase 1 - MVP",
      "features": ["FEAT-001", "FEAT-002"],
      "description": "Core features for initial launch"
    }
  ]
}

Focus on creating a logical, implementable feature roadmap that balances user value with technical feasibility."""
            
            # Prepare user prompt with requirements
            user_prompt = f"""Convert the following requirements into a prioritized feature roadmap:

{json.dumps(prd_state.requirements, indent=2)}

Please analyze these requirements and create a comprehensive feature roadmap following the MoSCoW prioritization method. Consider:
- User value and business impact
- Technical complexity and dependencies
- Implementation sequence
- MVP definition and release phases

Return only valid JSON that can be parsed."""
            
            # Make AI call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model = context.settings.get("define_features_model", "z-ai/glm-4.6")
            response = await self._call_ai(messages, model, context, state, temperature=0.4)
            
            # Parse and validate the response
            try:
                features_data = json.loads(response)
                
                # Validate structure
                required_sections = ["features", "feature_roadmap", "release_phases"]
                
                for section in required_sections:
                    if section not in features_data:
                        raise ValueError(f"Missing required section: {section}")
                
                # Calculate prioritization quality
                total_features = features_data["feature_roadmap"]["total_features"]
                priority_dist = features_data["feature_roadmap"]["priority_distribution"]
                
                # Good prioritization has reasonable distribution (not all MUST or all COULD)
                must_ratio = priority_dist.get("M", 0) / max(total_features, 1)
                should_ratio = priority_dist.get("S", 0) / max(total_features, 1)
                
                # Quality score based on balanced prioritization
                prioritization_quality = 1.0 - abs(0.3 - must_ratio) - abs(0.4 - should_ratio)
                prioritization_quality = max(0.0, min(1.0, prioritization_quality))
                
                # Store result
                result = {
                    "features": features_data,
                    "total_features": total_features,
                    "prioritization_quality": prioritization_quality,
                    "must_have_count": priority_dist.get("M", 0),
                    "should_have_count": priority_dist.get("S", 0),
                    "model_used": model,
                }
                
                # Update state quality metrics
                prd_state.feature_prioritization_quality = prioritization_quality
                
                # Update the original state with PRD-specific attributes
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump()
                    state_dict.update(prd_state.model_dump())
                    for key, value in state_dict.items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                
                self.logger.info(f"Successfully defined {total_features} features with prioritization")
                return result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse features JSON: {e}")
                raise PRDNodeException(f"Invalid JSON response from AI: {e}")
            
        except Exception as e:
            self.logger.error(f"Feature definition failed: {e}")
            raise PRDNodeException(f"Feature definition failed: {str(e)}") from e


class SetMetricsNode(PRDBaseNode):
    """
    Node for defining success metrics and KPIs.
    
    Takes features and requirements and defines measurable success
    criteria and key performance indicators.
    """
    
    def __init__(self):
        super().__init__("set_metrics")
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Define success metrics and KPIs.
        
        Args:
            state: Current PRD workflow state
            context: Workflow execution context
            
        Returns:
            Success metrics and KPIs structure
        """
        try:
            # Cast to PRDState to access PRD-specific attributes
            prd_state = state if isinstance(state, PRDState) else PRDState(**state.model_dump())
            
            self.logger.info("Defining success metrics and KPIs")
            
            # Prepare system prompt for metrics definition
            system_prompt = """You are a expert product analyst and data scientist.

Your task is to define comprehensive success metrics and KPIs for the product based on requirements and features.

Define metrics in these categories:
1. User Engagement Metrics - How users interact with the product
2. Business Metrics - Revenue, growth, market impact
3. Technical Metrics - Performance, reliability, quality
4. Quality Metrics - User satisfaction, error rates, etc.
5. Adoption Metrics - User acquisition, retention, growth

For each metric, provide:
- Metric name and description
- Measurement method (how to track)
- Target values (short-term, long-term)
- Success criteria (what constitutes success)
- Data sources required
- Frequency of measurement

Format your response as structured JSON:
{
  "success_metrics": {
    "user_engagement": [
      {
        "name": "Daily Active Users (DAU)",
        "description": "Number of unique users per day",
        "measurement": "Track user logins with unique identifiers",
        "targets": {
          "short_term": "1,000 DAU within 3 months",
          "long_term": "10,000 DAU within 12 months"
        },
        "success_criteria": "Consistent upward trend, >20% month-over-month growth",
        "data_sources": "User authentication logs, analytics platform",
        "measurement_frequency": "Daily"
      }
    ],
    "business": [
      {
        "name": "Revenue Growth",
        "description": "Monthly recurring revenue growth rate",
        "measurement": "Track subscription revenue and payments",
        "targets": {
          "short_term": "$10K MRR within 6 months",
          "long_term": "$100K MRR within 18 months"
        },
        "success_criteria": ">15% month-over-month growth",
        "data_sources": "Payment processor, billing system",
        "measurement_frequency": "Monthly"
      }
    ],
    "technical": [
      {
        "name": "System Uptime",
        "description": "Percentage of time system is available",
        "measurement": "Monitor service health and response times",
        "targets": {
          "short_term": "99.5% uptime",
          "long_term": "99.9% uptime"
        },
        "success_criteria": "Consistent uptime >99.5%",
        "data_sources": "Infrastructure monitoring, health checks",
        "measurement_frequency": "Real-time"
      }
    ],
    "quality": [
      {
        "name": "User Satisfaction Score",
        "description": "Net Promoter Score or user satisfaction rating",
        "measurement": "Regular user surveys and feedback collection",
        "targets": {
          "short_term": "NPS > 40 within 6 months",
          "long_term": "NPS > 60 within 12 months"
        },
        "success_criteria": "Positive trend in user satisfaction",
        "data_sources": "User surveys, feedback forms, app reviews",
        "measurement_frequency": "Quarterly"
      }
    ],
    "adoption": [
      {
        "name": "User Retention Rate",
        "description": "Percentage of users who continue using the product",
        "measurement": "Track user cohorts over time",
        "targets": {
          "short_term": "70% retention after 30 days",
          "long_term": "80% retention after 90 days"
        },
        "success_criteria": "Improving retention rates over time",
        "data_sources": "User activity logs, cohort analysis",
        "measurement_frequency": "Monthly"
      }
    ]
  },
  "kpi_dashboard": {
    "primary_kpis": ["DAU", "Revenue", "User Satisfaction"],
    "secondary_kpis": ["Uptime", "Retention", "Feature Adoption"],
    "monitoring_tools": ["Analytics platform", "Infrastructure monitoring", "Survey tools"]
  },
  "metrics_summary": {
    "total_metrics": 0,
    "by_category": {"user_engagement": 0, "business": 0, "technical": 0, "quality": 0, "adoption": 0},
    "measurement_frequency": {"real_time": 0, "daily": 0, "weekly": 0, "monthly": 0, "quarterly": 0}
  }
}

Focus on metrics that are actionable, measurable, and directly tied to product success."""
            
            # Prepare user prompt with requirements and features
            context_data = {
                "requirements": prd_state.requirements,
                "features": prd_state.features
            }
            
            user_prompt = f"""Define comprehensive success metrics and KPIs for the following product:

Requirements and Features:
{json.dumps(context_data, indent=2)}

Please analyze this product and define measurable success metrics that will help track progress and success. Consider:
- What success looks like for this product
- How to measure user value and business impact
- Technical quality and performance indicators
- User satisfaction and adoption metrics

Return only valid JSON that can be parsed."""
            
            # Make AI call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model = context.settings.get("set_metrics_model", "z-ai/glm-4.6")
            response = await self._call_ai(messages, model, context, state, temperature=0.3)
            
            # Parse and validate the response
            try:
                metrics_data = json.loads(response)
                
                # Validate structure
                required_sections = ["success_metrics", "kpi_dashboard", "metrics_summary"]
                
                for section in required_sections:
                    if section not in metrics_data:
                        raise ValueError(f"Missing required section: {section}")
                
                # Calculate metrics specificity
                total_metrics = metrics_data["metrics_summary"]["total_metrics"]
                category_coverage = len([cat for cat, count in metrics_data["metrics_summary"]["by_category"].items() if count > 0])
                
                # Specificity score based on coverage and detail
                specificity_score = (total_metrics / 20.0) * 0.5 + (category_coverage / 5.0) * 0.5
                specificity_score = min(1.0, specificity_score)
                
                # Store result
                result = {
                    "success_metrics": metrics_data,
                    "total_metrics": total_metrics,
                    "specificity_score": specificity_score,
                    "category_coverage": category_coverage,
                    "model_used": model,
                }
                
                # Update state quality metrics
                prd_state.metrics_specificity = specificity_score
                
                # Update the original state with PRD-specific attributes
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump()
                    state_dict.update(prd_state.model_dump())
                    for key, value in state_dict.items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                
                self.logger.info(f"Successfully defined {total_metrics} success metrics")
                return result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse metrics JSON: {e}")
                raise PRDNodeException(f"Invalid JSON response from AI: {e}")
            
        except Exception as e:
            self.logger.error(f"Metrics definition failed: {e}")
            raise PRDNodeException(f"Metrics definition failed: {str(e)}") from e


class GeneratePRDNode(PRDBaseNode):
    """
    Node for generating the complete PRD document.
    
    Takes all previous outputs and generates a comprehensive
    PRD document in Markdown format.
    """
    
    def __init__(self):
        super().__init__("generate_prd")
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Generate complete PRD document.
        
        Args:
            state: Current PRD workflow state
            context: Workflow execution context
            
        Returns:
            Generated PRD document content
        """
        try:
            # Cast to PRDState to access PRD-specific attributes
            prd_state = state if isinstance(state, PRDState) else PRDState(**state.model_dump())
            
            self.logger.info("Generating complete PRD document")
            
            # Prepare system prompt for PRD generation
            system_prompt = """You are a expert technical writer and product manager.

Your task is to create a comprehensive Product Requirements Document (PRD) in Markdown format using the provided research, requirements, features, and metrics.

The PRD should include these sections:
1. Executive Summary - High-level overview and goals
2. Problem Statement - What problem we're solving
3. Target Users - Who we're building this for
4. Requirements - Functional and non-functional requirements
5. Features - Prioritized feature list with user stories
6. Success Metrics - KPIs and measurement criteria
7. Technical Architecture - High-level technical approach
8. Timeline & Milestones - Suggested development phases
9. Assumptions & Constraints - Limitations and dependencies
10. Appendices - Additional details and references

Format guidelines:
- Use proper Markdown headers (#, ##, ###)
- Include tables for structured data
- Use bullet points for lists
- Include code blocks for technical details
- Add emphasis for important points
- Ensure professional, clear formatting

Focus on creating a document that is:
- Clear and comprehensive
- Well-structured and organized
- Actionable for development teams
- Professional in presentation
- Complete with all necessary details"""
            
            # Prepare user prompt with all previous outputs
            prd_context = {
                "research_summary": prd_state.research_summary,
                "requirements": prd_state.requirements,
                "features": prd_state.features,
                "success_metrics": prd_state.success_metrics,
                "version": prd_state.version,
                "last_updated": prd_state._get_timestamp() if hasattr(prd_state, '_get_timestamp') else None
            }
            
            user_prompt = f"""Generate a comprehensive Product Requirements Document (PRD) from the following information:

{json.dumps(prd_context, indent=2, default=str)}

Please create a well-formatted Markdown PRD that includes all standard sections and provides clear guidance for the development team. The document should be:
- Professional and comprehensive
- Well-structured with proper Markdown formatting
- Clear and actionable
- Complete with all necessary details for development

Generate the complete PRD document in Markdown format."""
            
            # Make AI call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model = context.settings.get("generate_prd_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.2)
            
            # Store result
            result = {
                "prd_content": response,
                "document_length": len(response),
                "section_count": response.count('#'),  # Count Markdown headers
                "model_used": model,
                "generation_timestamp": state._get_timestamp() if hasattr(state, '_get_timestamp') else None,
            }
            
            # Calculate document coherence (basic heuristic)
            coherence_score = min(1.0, result["section_count"] / 10.0)  # At least 10 sections for good structure
            prd_state.document_coherence = coherence_score
            
            # Update the original state with PRD-specific attributes
            if hasattr(state, 'model_dump'):
                state_dict = state.model_dump()
                state_dict.update(prd_state.model_dump())
                for key, value in state_dict.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
            
            self.logger.info(f"Successfully generated PRD document ({len(response)} characters)")
            return result
            
        except Exception as e:
            self.logger.error(f"PRD generation failed: {e}")
            raise PRDNodeException(f"PRD generation failed: {str(e)}") from e


class ReviewFormatNode(PRDBaseNode):
    """
    Node for reviewing and formatting the final PRD.
    
    Takes the generated PRD and reviews it for completeness,
    consistency, and proper formatting.
    """
    
    def __init__(self):
        super().__init__("review_format")
    
    async def execute(
        self,
        state: WorkflowState,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Review and format the final PRD.
        
        Args:
            state: Current PRD workflow state
            context: Workflow execution context
            
        Returns:
            Final polished PRD document
        """
        try:
            # Cast to PRDState to access PRD-specific attributes
            prd_state = state if isinstance(state, PRDState) else PRDState(**state.model_dump())
            
            self.logger.info("Reviewing and formatting final PRD")
            
            # Prepare system prompt for PRD review
            system_prompt = """You are a expert technical editor and quality assurance specialist.

Your task is to review and polish the generated Product Requirements Document (PRD) for:
1. Completeness - All required sections are present
2. Consistency - Information is consistent throughout
3. Clarity - Language is clear and unambiguous
4. Formatting - Proper Markdown formatting and structure
5. Quality - Professional presentation and accuracy

Review checklist:
- Executive summary is compelling and accurate
- Problem statement is clear and well-defined
- Target users are properly identified
- Requirements are complete and testable
- Features are properly prioritized and described
- Success metrics are specific and measurable
- Technical architecture is appropriate
- Timeline is realistic and well-structured
- Document flows logically and is easy to follow

Format your response as:
{
  "review_summary": {
    "overall_quality_score": 0.0,
    "completeness_score": 0.0,
    "consistency_score": 0.0,
    "clarity_score": 0.0,
    "formatting_score": 0.0
  },
  "issues_found": [
    {
      "section": "Section name",
      "issue": "Description of issue",
      "severity": "Critical|Major|Minor",
      "suggestion": "How to fix it"
    }
  ],
  "improvements_made": [
    "Description of improvements applied"
  ],
  "final_prd": "Complete polished PRD content"
}

Focus on creating a high-quality, professional document that development teams can rely on."""
            
            # Prepare user prompt with generated PRD
            user_prompt = f"""Review and polish the following Product Requirements Document:

Generated PRD:
{prd_state.prd_content}

Context information:
- Research summary: {json.dumps(prd_state.research_summary, indent=2, default=str)}
- Requirements: {json.dumps(prd_state.requirements, indent=2, default=str)}
- Features: {json.dumps(prd_state.features, indent=2, default=str)}
- Success metrics: {json.dumps(prd_state.success_metrics, indent=2, default=str)}

Please review this PRD for completeness, consistency, clarity, and formatting. Make any necessary improvements to create a professional, high-quality document. Return the complete polished PRD along with your review assessment.

Return only valid JSON that can be parsed."""
            
            # Make AI call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            model = context.settings.get("review_format_model", "z-ai/glm-4.6")
            response = await self._call_ai(messages, model, context, state, temperature=0.1)
            
            # Parse and validate the response
            try:
                review_data = json.loads(response)
                
                # Validate structure
                required_sections = ["review_summary", "issues_found", "improvements_made", "final_prd"]
                
                for section in required_sections:
                    if section not in review_data:
                        raise ValueError(f"Missing required section: {section}")
                
                # Extract final PRD
                final_prd = review_data["final_prd"]
                review_summary = review_data["review_summary"]
                
                # Store result
                result = {
                    "final_prd": final_prd,
                    "review_summary": review_summary,
                    "issues_found": len(review_data["issues_found"]),
                    "improvements_made": len(review_data["improvements_made"]),
                    "final_document_length": len(final_prd),
                    "model_used": model,
                }
                
                # Update final state
                prd_state.final_prd = final_prd
                prd_state.last_updated = prd_state._get_timestamp() if hasattr(prd_state, '_get_timestamp') else None
                
                # Update the original state with PRD-specific attributes
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump()
                    state_dict.update(prd_state.model_dump())
                    for key, value in state_dict.items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                
                self.logger.info(f"Successfully reviewed and finalized PRD ({len(final_prd)} characters)")
                return result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse review JSON: {e}")
                # If JSON parsing fails, treat the response as the final PRD
                result = {
                    "final_prd": response,
                    "review_summary": {"overall_quality_score": 0.8},
                    "issues_found": 0,
                    "improvements_made": 0,
                    "final_document_length": len(response),
                    "model_used": model,
                }
                
                prd_state.final_prd = response
                prd_state.last_updated = prd_state._get_timestamp() if hasattr(prd_state, '_get_timestamp') else None
                
                # Update the original state with PRD-specific attributes
                if hasattr(state, 'model_dump'):
                    state_dict = state.model_dump()
                    state_dict.update(prd_state.model_dump())
                    for key, value in state_dict.items():
                        if hasattr(state, key):
                            setattr(state, key, value)
                
                return result
            
        except Exception as e:
            self.logger.error(f"PRD review failed: {e}")
            raise PRDNodeException(f"PRD review failed: {str(e)}") from e