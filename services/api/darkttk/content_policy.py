import json
import unicodedata
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BlockedTopic, ModerationCheck

POLICY_VERSION = "2026-07"
PROHIBITED_RULES = {
    "politics": ("politica", "partido politico", "eleicao", "candidato"),
    "religion": ("religiao", "conversao religiosa", "culto religioso"),
    "sexual_content": ("conteudo sexual", "sexo explicito", "pornografia"),
    "hate_extremism": ("discurso de odio", "supremacismo", "extremismo"),
    "graphic_violence": ("violencia grafica", "tortura explicita"),
    "self_harm": ("automutilacao", "suicidio"),
    "illegal_drugs": ("drogas ilicitas", "cocaina", "trafico de drogas"),
    "scams": ("golpe financeiro", "dinheiro garantido", "renda garantida"),
    "medical_advice": ("diagnostico medico", "prescricao medica", "pare de tomar"),
    "guaranteed_returns": ("retorno garantido", "lucro garantido", "sem risco"),
    "copyright_infringement": ("filme completo", "cena completa sem autorizacao"),
}
REVIEW_RULES = {
    "health": ("saude", "doenca", "tratamento", "sintoma"),
    "finance": ("investimento", "acoes", "criptomoeda", "financas"),
    "science": ("estudo cientifico", "pesquisa prova", "cientificamente comprovado"),
    "minors": ("crianca", "adolescente", "menor de idade"),
}


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return " ".join(
        "".join(char for char in decomposed if not unicodedata.combining(char))
        .lower()
        .split()
    )


@dataclass(frozen=True)
class ModerationDecision:
    result: str
    matched_rules: list[str]


def moderate(db: Session, organization_id: str, text: str) -> ModerationDecision:
    normalized = normalize(text)
    blocked = [
        rule
        for rule, terms in PROHIBITED_RULES.items()
        if any(term in normalized for term in terms)
    ]
    custom = list(
        db.scalars(
            select(BlockedTopic).where(
                BlockedTopic.organization_id == organization_id,
                BlockedTopic.active.is_(True),
            )
        )
    )
    blocked.extend(
        f"custom:{item.kind}:{item.term}"
        for item in custom
        if item.normalized_term in normalized
    )
    if blocked:
        return ModerationDecision("block", sorted(set(blocked)))
    review = [
        rule
        for rule, terms in REVIEW_RULES.items()
        if any(term in normalized for term in terms)
    ]
    return ModerationDecision("review" if review else "allow", sorted(set(review)))


def record_moderation(
    db: Session,
    *,
    organization_id: str,
    subject_type: str,
    subject_id: str,
    stage: str,
    decision: ModerationDecision,
) -> None:
    db.add(
        ModerationCheck(
            organization_id=organization_id,
            subject_type=subject_type,
            subject_id=subject_id,
            stage=stage,
            result=decision.result,
            matched_rules_json=json.dumps(decision.matched_rules, ensure_ascii=False),
            policy_version=POLICY_VERSION,
        )
    )
