"""
Workflow nodes package.

This package contains all workflow node implementations
for different types of AI agents and processing steps.
"""

from .base import BaseNode
from .research_nodes import (
    AnalyzeIdeaNode, MarketResearchNode, CompetitiveAnalysisNode,
    TechnicalFeasibilityNode, SynthesizeResearchNode, ResearchNodeException
)
from .prd_nodes import (
    ExtractRequirementsNode, DefineFeaturesNode, SetMetricsNode,
    GeneratePRDNode, ReviewFormatNode, PRDNodeException
)

# Create a ResearchNode alias for AnalyzeIdeaNode for compatibility
ResearchNode = AnalyzeIdeaNode

# Create placeholder nodes for missing imports
class ArchitectNode(BaseNode):
    """Placeholder architect node."""
    def __init__(self):
        super().__init__("architect")

class ImplementNode(BaseNode):
    """Placeholder implement node."""
    def __init__(self):
        super().__init__("implement")

class DebugNode(BaseNode):
    """Placeholder debug node."""
    def __init__(self):
        super().__init__("debug")

class MemoryIngestionNode(BaseNode):
    """Placeholder memory ingestion node."""
    def __init__(self):
        super().__init__("memory_ingestion")

__all__ = [
    "BaseNode",
    "AnalyzeIdeaNode",
    "MarketResearchNode",
    "CompetitiveAnalysisNode",
    "TechnicalFeasibilityNode",
    "SynthesizeResearchNode",
    "ResearchNodeException",
    "ExtractRequirementsNode",
    "DefineFeaturesNode",
    "SetMetricsNode",
    "GeneratePRDNode",
    "ReviewFormatNode",
    "PRDNodeException",
    "ResearchNode",
    "ArchitectNode",
    "ImplementNode",
    "DebugNode",
    "MemoryIngestionNode",
]