from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AiProvider, ContentNiche

DEFAULT_NICHES = (
    ("Saúde e bem-estar", "saude-bem-estar", "Informação geral, hábitos e bem-estar sem diagnóstico."),
    ("Educação", "educacao", "Explicações didáticas e aprendizado."),
    ("Disciplina", "disciplina", "Hábitos, constância e responsabilidade."),
    ("Compromisso", "compromisso", "Consistência e cumprimento de objetivos."),
    ("Motivação", "motivacao", "Conteúdo inspirador sem promessas enganosas."),
    ("Curiosidades", "curiosidades", "Fatos interessantes com fontes."),
    ("História", "historia", "Contexto histórico e narrativas documentais."),
    ("Ciência", "ciencia", "Divulgação científica verificável."),
    ("Engenharia", "engenharia", "Estruturas, processos e soluções técnicas."),
    ("Finanças pessoais", "financas-pessoais", "Educação financeira sem retorno garantido."),
    ("Tecnologia", "tecnologia", "Produtos, conceitos e tendências tecnológicas."),
    ("Desenvolvimento pessoal", "desenvolvimento-pessoal", "Habilidades e autoconsciência."),
    ("Produtividade", "produtividade", "Métodos, organização e foco."),
    ("Cinema e entretenimento", "cinema-entretenimento", "Análises e comentários transformativos."),
    ("Resumos e análises de filmes", "analises-filmes", "Análises originais com cuidado autoral."),
    ("Conteúdo personalizado", "personalizado", "Pautas definidas pelo usuário."),
)


def ensure_content_defaults(db: Session, organization_id: str) -> None:
    if not db.scalar(
        select(ContentNiche.id).where(ContentNiche.organization_id == organization_id).limit(1)
    ):
        db.add_all(
            [
                ContentNiche(
                    organization_id=organization_id,
                    name=name,
                    slug=slug,
                    description=description,
                )
                for name, slug, description in DEFAULT_NICHES
            ]
        )
    if not db.scalar(
        select(AiProvider.id)
        .where(
            AiProvider.organization_id == organization_id,
            AiProvider.provider_key == "mock-local-v1",
        )
        .limit(1)
    ):
        db.add_all(
            [
                AiProvider(
                    organization_id=organization_id,
                    capability="language_model",
                    provider_key="mock-local-v1",
                    display_name="Adaptador local de desenvolvimento",
                    enabled=True,
                    is_mock=True,
                ),
                AiProvider(
                    organization_id=organization_id,
                    capability="fact_check",
                    provider_key="mock-fact-check-v1",
                    display_name="Verificador local de desenvolvimento",
                    enabled=True,
                    is_mock=True,
                ),
            ]
        )
    if not db.scalar(
        select(AiProvider.id)
        .where(
            AiProvider.organization_id == organization_id,
            AiProvider.provider_key == "mock-tts-v1",
        )
        .limit(1)
    ):
        db.add(
            AiProvider(
                organization_id=organization_id,
                capability="text_to_speech",
                provider_key="mock-tts-v1",
                display_name="Narrador local de desenvolvimento",
                enabled=True,
                is_mock=True,
            )
        )
    db.flush()
