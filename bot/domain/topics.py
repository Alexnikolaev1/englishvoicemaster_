"""Single source of truth for conversation topics."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    starter: str


TOPICS: tuple[Topic, ...] = (
    Topic(
        key="restaurant",
        label="🍽️ At the Restaurant",
        starter="Great! Let's practice restaurant English. Imagine you're at a nice restaurant. What would you like to order?",
    ),
    Topic(
        key="interview",
        label="💼 Job Interview",
        starter="Perfect choice! You're in a job interview. Tell me: what are your greatest strengths?",
    ),
    Topic(
        key="travel",
        label="✈️ Travel & Tourism",
        starter="Wonderful! Let's talk travel. Tell me about the best trip you've ever taken, or somewhere you'd love to go.",
    ),
    Topic(
        key="daily",
        label="🏠 Daily Life",
        starter="Great! Let's talk about your typical day. Walk me through your morning routine!",
    ),
    Topic(
        key="shopping",
        label="💰 Shopping & Money",
        starter="Let's talk shopping! Describe your last big purchase — what did you buy and why?",
    ),
    Topic(
        key="movies",
        label="🎬 Movies & Culture",
        starter="Fun topic! Tell me about a movie or TV show you've watched recently. What did you think of it?",
    ),
    Topic(
        key="health",
        label="💪 Health & Sport",
        starter="Let's get active with our vocabulary! Do you have any sports or fitness hobbies?",
    ),
    Topic(
        key="smalltalk",
        label="🤝 Small Talk",
        starter="Let's chat! Tell me a bit about yourself — where are you from and what do you do?",
    ),
    Topic(
        key="tech",
        label="💻 Technology",
        starter="Interesting topic! How has technology changed your daily life in the last few years?",
    ),
    Topic(
        key="environment",
        label="🌍 Environment",
        starter="Important topic! What environmental issues concern you most, and what do you do in your daily life to help?",
    ),
)

TOPIC_BY_KEY = {topic.key: topic for topic in TOPICS}
TOPIC_LABEL_TO_STARTER = {topic.label: topic.starter for topic in TOPICS}

