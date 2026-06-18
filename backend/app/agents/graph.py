from langgraph.graph import END, StateGraph

from app.agents.fundamentals import fundamentals_agent
from app.agents.news import news_agent
from app.agents.sec import sec_agent
from app.agents.sentiment import sentiment_agent
from app.agents.synthesis import synthesis_agent
from app.models.state import WatchmanState


def build_graph():
    """Builds the Watchman LangGraph pipeline.

    Pipeline: news -> fundamentals -> sentiment -> sec -> synthesis -> END
    """
    graph = StateGraph(WatchmanState)

    graph.add_node("news", news_agent)
    graph.add_node("fundamentals", fundamentals_agent)
    graph.add_node("sentiment", sentiment_agent)
    graph.add_node("sec", sec_agent)
    graph.add_node("synthesis", synthesis_agent)

    graph.set_entry_point("news")
    graph.add_edge("news", "fundamentals")
    graph.add_edge("fundamentals", "sentiment")
    graph.add_edge("sentiment", "sec")
    graph.add_edge("sec", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()


watchman_graph = build_graph()
