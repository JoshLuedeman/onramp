"""Questionnaire models for the adaptive questionnaire engine."""

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class QuestionCategory(Base, TimestampMixin):
    __tablename__ = "question_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    caf_design_area: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="category")


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question_categories.id"), nullable=False
    )
    category: Mapped["QuestionCategory"] = relationship("QuestionCategory", back_populates="questions")

    # Branching: only show this question if a specific answer was given
    depends_on_question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("questions.id"), nullable=True
    )
    depends_on_answer: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Org size targeting
    min_org_size: Mapped[str | None] = mapped_column(String(20), nullable=True)


class QuestionnaireResponse(Base, TimestampMixin):
    __tablename__ = "questionnaire_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    answer_value: Mapped[str] = mapped_column(Text, nullable=False)
    answer_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    project: Mapped["Project"] = relationship("Project", back_populates="questionnaire_responses")

    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id"), nullable=False
    )
