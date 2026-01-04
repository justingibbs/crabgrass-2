"""
Demo data seeding for Crabgrass.

Run with: uv run python -m crabgrass.seed

Creates sample ideas, objectives, context files, and conversation history
for demonstration purposes.
"""

import uuid
from datetime import datetime, timezone

import structlog

from .db.connection import get_db
from .db.migrations import (
    SALLY_USER_ID,
    SAM_USER_ID,
    ACME_ORG_ID,
    run_migrations,
)
from .concepts.idea import IdeaConcept
from .concepts.objective import ObjectiveConcept
from .concepts.kernel_file import KernelFileConcept
from .concepts.context_file import ContextFileConcept
from .concepts.session import SessionConcept
from .concepts.objective_file import ObjectiveFileConcept
from .sync.synchronizations import (
    on_idea_created,
    on_objective_created,
    on_kernel_file_updated,
    on_idea_linked_to_objective,
)

logger = structlog.get_logger()

# Pre-defined IDs for demo data (stable across resets)
DEMO_OBJECTIVE_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")
DEMO_IDEA_1_ID = uuid.UUID("00000000-0000-0000-0000-000000000200")
DEMO_IDEA_2_ID = uuid.UUID("00000000-0000-0000-0000-000000000201")
DEMO_IDEA_3_ID = uuid.UUID("00000000-0000-0000-0000-000000000202")


def seed_demo_data():
    """Seed demo data for the application."""
    logger.info("seeding_demo_data")

    # Ensure migrations have run
    run_migrations()

    # Check if demo data already exists
    with get_db() as db:
        result = db.execute(
            "SELECT id FROM ideas WHERE id = ?",
            [str(DEMO_IDEA_1_ID)],
        ).fetchone()
        if result:
            logger.info("demo_data_already_exists")
            return

    # Initialize concepts
    idea_concept = IdeaConcept()
    objective_concept = ObjectiveConcept()
    kernel_file_concept = KernelFileConcept()
    context_file_concept = ContextFileConcept()
    session_concept = SessionConcept()
    objective_file_concept = ObjectiveFileConcept()

    # --- Create Demo Objective ---
    logger.info("creating_demo_objective")

    objective = objective_concept.create(
        org_id=ACME_ORG_ID,
        title="Improve Customer Experience",
        description="Enhance customer satisfaction through better service and product quality",
        owner_id=SAM_USER_ID,
        timeframe="Q1 2026",
        created_by=SAM_USER_ID,
    )

    # Update the objective file with meaningful content
    objective_file_concept.update(
        objective.id,
        """# Improve Customer Experience

Our goal is to significantly enhance customer satisfaction across all touchpoints.

## Why This Matters

Customer experience is the primary differentiator in today's competitive market. Poor experiences lead to churn, while exceptional experiences drive loyalty and word-of-mouth growth.

## Success Criteria

- Increase NPS score from 42 to 60 by end of Q1
- Reduce customer support ticket resolution time by 30%
- Achieve 90% positive feedback on new product features
- Decrease customer churn rate by 15%
""",
        SAM_USER_ID,
    )

    on_objective_created(objective, SAM_USER_ID)

    # --- Create Demo Idea 1: Fully Complete ---
    logger.info("creating_demo_idea_1")

    # Create directly in DB with fixed ID
    now = datetime.now(timezone.utc)
    with get_db() as db:
        db.execute(
            """
            INSERT INTO ideas (id, org_id, creator_id, objective_id, title, status, kernel_completion, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(DEMO_IDEA_1_ID),
                str(ACME_ORG_ID),
                str(SALLY_USER_ID),
                str(objective.id),
                "AI-Powered Customer Support Chatbot",
                "active",
                4,
                now.isoformat(),
                now.isoformat(),
            ],
        )

    # Initialize kernel files manually
    kernel_file_concept.initialize_all(DEMO_IDEA_1_ID, SALLY_USER_ID)

    # Update kernel files with complete content
    idea1_summary = """# AI-Powered Customer Support Chatbot

An intelligent chatbot that handles 80% of common customer inquiries instantly, freeing up human agents to focus on complex issues that require empathy and creative problem-solving.

The chatbot uses natural language understanding to comprehend customer intent and provide accurate, contextual responses from our knowledge base.
"""

    idea1_challenge = """# The Challenge

**Problem:** Our customer support team is overwhelmed with repetitive queries. 65% of tickets are about order status, password resets, and basic product questions. This leads to:

- Average wait time of 45 minutes for customers
- Agent burnout and high turnover (35% annually)
- Inability to provide 24/7 support

**Who experiences this:** Every customer who needs help, and our support team of 50 agents.

**Why it matters:** Customer satisfaction scores have dropped 15 points in the last year, directly correlating with support wait times.
"""

    idea1_approach = """# Our Approach

**Solution:** Deploy an AI chatbot integrated with our existing CRM and knowledge base.

**Key differentiators:**
1. **Contextual awareness** - The bot knows the customer's order history and recent interactions
2. **Seamless handoff** - When the bot can't help, it transfers to a human with full conversation context
3. **Continuous learning** - Every resolved ticket improves the model

**Technical approach:**
- Use fine-tuned LLM with RAG on our knowledge base
- Integrate with Zendesk and Shopify APIs
- Build feedback loop for model improvement
"""

    idea1_steps = """# Coherent Steps

1. **Week 1-2:** Audit current support tickets to identify top 20 query patterns
2. **Week 3-4:** Build RAG pipeline with knowledge base integration
3. **Week 5-6:** Develop Zendesk and Shopify API integrations
4. **Week 7-8:** Create handoff protocol and agent dashboard
5. **Week 9-10:** Beta test with 10% of traffic, gather feedback
6. **Week 11-12:** Full rollout with monitoring dashboard

**Owners:**
- Knowledge base integration: Sarah (Backend)
- Chat UI: Mike (Frontend)
- API integrations: David (Platform)
"""

    kernel_file_concept.update(DEMO_IDEA_1_ID, "summary", idea1_summary, SALLY_USER_ID)
    kernel_file_concept.update(DEMO_IDEA_1_ID, "challenge", idea1_challenge, SALLY_USER_ID)
    kernel_file_concept.update(DEMO_IDEA_1_ID, "approach", idea1_approach, SALLY_USER_ID)
    kernel_file_concept.update(DEMO_IDEA_1_ID, "coherent_steps", idea1_steps, SALLY_USER_ID)

    # Mark all as complete
    kernel_file_concept.mark_complete(DEMO_IDEA_1_ID, "summary")
    kernel_file_concept.mark_complete(DEMO_IDEA_1_ID, "challenge")
    kernel_file_concept.mark_complete(DEMO_IDEA_1_ID, "approach")
    kernel_file_concept.mark_complete(DEMO_IDEA_1_ID, "coherent_steps")

    # Link to objective
    on_idea_linked_to_objective(DEMO_IDEA_1_ID, objective.id)

    # Add context file
    context_file_concept.create(
        idea_id=DEMO_IDEA_1_ID,
        filename="competitor-analysis.md",
        content="""# Competitor Chatbot Analysis

## Zendesk Answer Bot
- Basic keyword matching
- Limited context awareness
- $50/agent/month

## Intercom Fin
- GPT-4 powered
- Good for sales, less for support
- $99/agent/month

## Our Advantage
- Custom fine-tuning on our data
- Deep CRM integration
- Lower cost at scale
""",
        user_id=SALLY_USER_ID,
    )

    # Add conversation history
    session1 = session_concept.create(
        idea_id=DEMO_IDEA_1_ID,
        user_id=SALLY_USER_ID,
        agent_type="coherence",
        title="Initial planning discussion",
    )

    session_concept.add_message(
        session1.id,
        "user",
        "I've drafted the initial approach. Can you check if everything is coherent?",
    )

    session_concept.add_message(
        session1.id,
        "agent",
        """I've reviewed your kernel files and they show strong coherence. Here's my analysis:

**Strengths:**
- The Challenge clearly identifies a measurable problem (65% repetitive queries, 45-min wait times)
- The Approach directly addresses these issues with specific technical solutions
- The Steps are concrete with clear ownership and timelines

**One suggestion:** Consider adding a success metric to Steps - how will you measure the 80% query handling goal during beta testing?

Overall, this is a well-structured idea that's ready for execution.""",
    )

    # --- Create Demo Idea 2: Partially Complete (2/4 kernels) ---
    logger.info("creating_demo_idea_2")

    with get_db() as db:
        db.execute(
            """
            INSERT INTO ideas (id, org_id, creator_id, objective_id, title, status, kernel_completion, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(DEMO_IDEA_2_ID),
                str(ACME_ORG_ID),
                str(SALLY_USER_ID),
                None,
                "Proactive Order Status Notifications",
                "draft",
                2,
                now.isoformat(),
                now.isoformat(),
            ],
        )

    kernel_file_concept.initialize_all(DEMO_IDEA_2_ID, SALLY_USER_ID)

    idea2_summary = """# Proactive Order Status Notifications

A notification system that proactively updates customers about their order status via their preferred channel (SMS, email, or push), reducing "where's my order" inquiries by 50%.
"""

    idea2_challenge = """# The Challenge

**Problem:** "Where is my order?" makes up 30% of all support tickets. Customers feel anxious when they don't know their order status, leading to:

- Unnecessary support contacts
- Negative social media posts
- Cart abandonment on future purchases due to trust issues

**Who experiences this:** Any customer who places an order, especially first-time buyers.

**Why it matters:** Each WISMO ticket costs $5 to handle. With 10,000 monthly tickets, that's $50,000/month in preventable costs.
"""

    kernel_file_concept.update(DEMO_IDEA_2_ID, "summary", idea2_summary, SALLY_USER_ID)
    kernel_file_concept.update(DEMO_IDEA_2_ID, "challenge", idea2_challenge, SALLY_USER_ID)

    kernel_file_concept.mark_complete(DEMO_IDEA_2_ID, "summary")
    kernel_file_concept.mark_complete(DEMO_IDEA_2_ID, "challenge")

    # Add a conversation
    session2 = session_concept.create(
        idea_id=DEMO_IDEA_2_ID,
        user_id=SALLY_USER_ID,
        agent_type="approach",
        file_type="approach",
        title="Working on approach",
    )

    session_concept.add_message(
        session2.id,
        "user",
        "I'm not sure what technical approach to take. Any suggestions?",
    )

    session_concept.add_message(
        session2.id,
        "agent",
        """Great question! Here are some approaches to consider:

**Option 1: Event-driven webhooks**
- Subscribe to shipping carrier webhooks (FedEx, UPS, USPS)
- Trigger notifications on status changes
- Pros: Real-time, no polling
- Cons: Carrier integration complexity

**Option 2: Scheduled polling**
- Poll carrier APIs every 30 minutes
- Batch process updates
- Pros: Simpler implementation
- Cons: Slight delay in updates

**Option 3: Hybrid approach**
- Use webhooks where available
- Fall back to polling for carriers without webhooks
- Best of both worlds

I'd recommend starting with the hybrid approach. Would you like me to help you draft the technical architecture?""",
    )

    # --- Create Demo Idea 3: Just Started (0/4 kernels) ---
    logger.info("creating_demo_idea_3")

    with get_db() as db:
        db.execute(
            """
            INSERT INTO ideas (id, org_id, creator_id, objective_id, title, status, kernel_completion, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(DEMO_IDEA_3_ID),
                str(ACME_ORG_ID),
                str(SALLY_USER_ID),
                None,
                "Customer Feedback Loop System",
                "draft",
                0,
                now.isoformat(),
                now.isoformat(),
            ],
        )

    kernel_file_concept.initialize_all(DEMO_IDEA_3_ID, SALLY_USER_ID)

    logger.info(
        "demo_data_seeded",
        objective_count=1,
        idea_count=3,
    )


def main():
    """Entry point for the seed command."""
    import sys

    print("Seeding Crabgrass demo data...")
    try:
        seed_demo_data()
        print("Demo data seeded successfully!")
        print("\nCreated:")
        print("  - 1 Objective: 'Improve Customer Experience'")
        print("  - 3 Ideas:")
        print("    - AI-Powered Customer Support Chatbot (4/4 complete)")
        print("    - Proactive Order Status Notifications (2/4 complete)")
        print("    - Customer Feedback Loop System (0/4 complete)")
        print("\nLog in as Sally Chen to see the ideas.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
