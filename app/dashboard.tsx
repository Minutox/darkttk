"use client";

import { useEffect, useMemo, useState } from "react";
import type { RuntimeSnapshot } from "./api-client";

type DashboardProps = {
  userName: string;
  userEmail: string;
  runtime: RuntimeSnapshot;
};

type ApprovalStatus = "Pendente" | "Alterações" | "Aprovado" | "Reprovado";

type ApprovalItem = {
  id: number | string;
  videoProjectId?: string;
  title: string;
  niche: string;
  duration: string;
  score: number;
  status: ApprovalStatus;
  submitted: string;
  hook: string;
  note: string;
  mockPreview?: boolean;
};

type CalendarItem = {
  id: number | string;
  videoProjectId?: string;
  day: number;
  time: string;
  title: string;
  niche: string;
  status: "Reservado" | "Pronto";
};

type NotificationItem = {
  id: number | string;
  title: string;
  text: string;
  tone: string;
  read: boolean;
};

const navigation = [
  { label: "Visão geral", icon: "⌂" },
  { label: "Criar conteúdo", icon: "＋" },
  { label: "Fila de produção", icon: "◫" },
  { label: "Aprovações", icon: "✓" },
  { label: "Calendário", icon: "□" },
  { label: "Publicações", icon: "↗" },
  { label: "Biblioteca", icon: "▣" },
  { label: "Tendências", icon: "↗" },
  { label: "Séries", icon: "≡" },
  { label: "Editor visual", icon: "◫" },
  { label: "Métricas", icon: "⌁" },
  { label: "Experimentos", icon: "A/B" },
  { label: "Operações", icon: "◇" },
  { label: "Release RC1", icon: "RC" },
  { label: "Configurações", icon: "⚙" },
];

const initialApprovals: ApprovalItem[] = [
  {
    id: 1,
    title: "A ponte que cresce no verão",
    niche: "Engenharia",
    duration: "00:42",
    score: 92,
    status: "Pendente",
    submitted: "há 18 min",
    hook: "Pontes realmente mudam de tamanho — e isso evita danos estruturais.",
    note: "Validar a legenda dos segundos 12–16.",
    mockPreview: true,
  },
  {
    id: 2,
    title: "Por que bocejamos?",
    niche: "Ciência",
    duration: "00:38",
    score: 88,
    status: "Pendente",
    submitted: "há 42 min",
    hook: "O bocejo pode ser uma forma de o cérebro regular a própria temperatura.",
    note: "Fonte científica anexada ao roteiro.",
  },
  {
    id: 3,
    title: "A regra dos 2 minutos",
    niche: "Produtividade",
    duration: "00:31",
    score: 86,
    status: "Alterações",
    submitted: "ontem, 19:20",
    hook: "Se uma tarefa leva menos de dois minutos, resolva agora.",
    note: "CTA precisa ficar menos impositivo.",
  },
  {
    id: 4,
    title: "O paradoxo da escolha",
    niche: "Desenvolvimento pessoal",
    duration: "00:46",
    score: 90,
    status: "Aprovado",
    submitted: "ontem, 16:05",
    hook: "Mais opções nem sempre significam decisões melhores.",
    note: "Aprovado para a faixa das 18h30.",
  },
];

const initialCalendar: CalendarItem[] = [
  { id: 1, day: 24, time: "18:30", title: "O paradoxo da escolha", niche: "Desenvolvimento pessoal", status: "Pronto" },
  { id: 2, day: 24, time: "21:15", title: "3 erros que drenam sua energia", niche: "Produtividade", status: "Reservado" },
  { id: 3, day: 25, time: "12:10", title: "Como sensores enxergam objetos", niche: "Tecnologia", status: "Reservado" },
  { id: 4, day: 27, time: "19:40", title: "O concreto que se regenera", niche: "Engenharia", status: "Pronto" },
  { id: 5, day: 29, time: "18:20", title: "Por que sentimos déjà vu?", niche: "Ciência", status: "Reservado" },
];

const week = [
  { weekday: "SEX", day: 24 },
  { weekday: "SÁB", day: 25 },
  { weekday: "DOM", day: 26 },
  { weekday: "SEG", day: 27 },
  { weekday: "TER", day: 28 },
  { weekday: "QUA", day: 29 },
  { weekday: "QUI", day: 30 },
];

const notificationSeed = [
  { id: 1, title: "Nova revisão", text: "A ponte que cresce no verão aguarda decisão.", tone: "purple", read: false },
  { id: 2, title: "Horário reservado", text: "O paradoxo da escolha — hoje às 18:30.", tone: "green", read: false },
  { id: 3, title: "Alteração concluída", text: "A regra dos 2 minutos foi reenviada.", tone: "amber", read: false },
];

export default function Dashboard({ userName, userEmail, runtime }: DashboardProps) {
  const [active, setActive] = useState("Visão geral");
  const [approvals, setApprovals] = useState<ApprovalItem[]>(() => {
    if (runtime.mode !== "live" || !runtime.approvals) return initialApprovals;
    const statusMap: Record<string, ApprovalStatus> = {
      pending: "Pendente",
      approved: "Aprovado",
      rejected: "Reprovado",
      changes_requested: "Alterações",
    };
    return runtime.approvals.map((item) => ({
      id: item.id,
      videoProjectId: item.video_project_id,
      title: item.project_title,
      niche: "API DarkTTK",
      duration: "—",
      score: 0,
      status: statusMap[item.status] ?? "Pendente",
      submitted: new Date(item.created_at).toLocaleString("pt-BR"),
      hook: item.request_note || "Prévia vinculada ao projeto persistido.",
      note: item.decision_note || item.request_note || "",
      mockPreview: item.preview_is_mock,
    }));
  });
  const [calendar, setCalendar] = useState<CalendarItem[]>(() => {
    if (runtime.mode !== "live" || !runtime.calendar) return initialCalendar;
    return runtime.calendar.map((item) => {
      const scheduled = new Date(item.scheduled_for);
      return {
        id: item.id,
        videoProjectId: item.video_project_id,
        day: scheduled.getDate(),
        time: scheduled.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
        title: item.project_title,
        niche: "API DarkTTK",
        status: item.status === "ready" ? "Pronto" : "Reservado",
      };
    });
  });
  const [selected, setSelected] = useState<ApprovalItem | null>(null);
  const [decisionNote, setDecisionNote] = useState("");
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => {
    if (runtime.mode !== "live" || !runtime.notifications) return notificationSeed;
    return runtime.notifications.items.map((item) => ({
      id: item.id,
      title: item.title,
      text: item.message,
      tone: item.kind.includes("failed") ? "amber" : "green",
      read: Boolean(item.read_at),
    }));
  });
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleTitle, setScheduleTitle] = useState("A ponte que cresce no verão");
  const [scheduleDay, setScheduleDay] = useState(25);
  const [scheduleTime, setScheduleTime] = useState("18:30");
  const [toast, setToast] = useState("");
  const [filter, setFilter] = useState<"Todos" | ApprovalStatus>("Todos");
  const [search, setSearch] = useState("");

  const displayName = userName.includes("@") ? userName.split("@")[0] : userName.split(" ")[0];
  const initials = displayName.slice(0, 2).toUpperCase();
  const pendingCount = approvals.filter((item) => item.status === "Pendente").length;
  const unreadCount = notifications.filter((item) => !item.read).length;

  const filteredApprovals = useMemo(
    () =>
      approvals.filter((item) => {
        const matchesStatus = filter === "Todos" || item.status === filter;
        const matchesSearch = `${item.title} ${item.niche}`
          .toLocaleLowerCase("pt-BR")
          .includes(search.toLocaleLowerCase("pt-BR"));
        return matchesStatus && matchesSearch;
      }),
    [approvals, filter, search],
  );

  function flash(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2800);
  }

  function openReview(item: ApprovalItem) {
    setSelected(item);
    setDecisionNote(item.note);
  }

  async function decide(nextStatus: ApprovalStatus) {
    if (!selected) return;
    if ((nextStatus === "Alterações" || nextStatus === "Reprovado") && !decisionNote.trim()) {
      flash("Registre uma justificativa antes de concluir.");
      return;
    }
    if (runtime.mode === "live" && typeof selected.id === "string") {
      const decisionMap: Record<Exclude<ApprovalStatus, "Pendente">, string> = {
        Aprovado: "approved",
        Reprovado: "rejected",
        Alterações: "changes_requested",
      };
      if (nextStatus !== "Pendente") {
        const response = await fetch("/api/workflow", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "approval_decision",
            approval_id: selected.id,
            decision: decisionMap[nextStatus],
            note: decisionNote,
          }),
        });
        if (!response.ok) {
          flash("A decisão não foi persistida. Atualize a página e tente novamente.");
          return;
        }
      }
    }
    setApprovals((items) =>
      items.map((item) =>
        item.id === selected.id ? { ...item, status: nextStatus, note: decisionNote } : item,
      ),
    );
    setNotifications((items) => [
      {
        id: Date.now(),
        title: `Decisão registrada: ${nextStatus}`,
        text: selected.title,
        tone: nextStatus === "Aprovado" ? "green" : "amber",
        read: false,
      },
      ...items,
    ]);
    setSelected(null);
    flash(
      nextStatus === "Aprovado"
        ? "Vídeo aprovado. Ele já pode ser agendado."
        : "Decisão registrada no histórico editorial.",
    );
  }

  async function addSchedule() {
    if (calendar.some((item) => item.day === scheduleDay && item.time === scheduleTime)) {
      flash("Esse horário já está ocupado. Escolha outra faixa.");
      return;
    }
    const approval = approvals.find(
      (item) => item.title === scheduleTitle && item.status === "Aprovado",
    );
    let persistedId: string | number = Date.now();
    if (runtime.mode === "live") {
      if (!approval?.videoProjectId) {
        flash("Projeto aprovado não encontrado na API.");
        return;
      }
      const response = await fetch("/api/workflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "schedule",
          project_id: approval.videoProjectId,
          scheduled_for: `2026-07-${String(scheduleDay).padStart(2, "0")}T${scheduleTime}:00-03:00`,
          timezone: "America/Sao_Paulo",
        }),
      });
      if (!response.ok) {
        flash("O horário não foi persistido. Verifique conflitos e tente novamente.");
        return;
      }
      const persisted = await response.json() as { id: string };
      persistedId = persisted.id;
    }
    setCalendar((items) => [
      ...items,
      {
        id: persistedId,
        videoProjectId: approval?.videoProjectId,
        day: scheduleDay,
        time: scheduleTime,
        title: scheduleTitle,
        niche: "Conteúdo aprovado",
        status: "Reservado",
      },
    ]);
    setScheduleOpen(false);
    flash("Horário reservado no calendário editorial.");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">D</span>
          <span><b>DarkTTK</b><small>CONTENT INTELLIGENCE</small></span>
        </div>
        <nav aria-label="Navegação principal">
          <p>OPERAÇÃO</p>
          {navigation.slice(0, 10).map((item) => (
            <button
              key={item.label}
              className={active === item.label ? "nav-item active" : "nav-item"}
              onClick={() => {
                setActive(item.label);
              }}
            >
              <span>{item.icon}</span><b>{item.label}</b>
              {item.label === "Aprovações" && pendingCount > 0 && <em>{pendingCount}</em>}
            </button>
          ))}
          <p>INTELIGÊNCIA</p>
          {navigation.slice(10).map((item) => (
            <button
              key={item.label}
              className={active === item.label ? "nav-item active" : "nav-item"}
              onClick={() => setActive(item.label)}
            >
              <span>{item.icon}</span><b>{item.label}</b>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="usage"><span>Plano Pro</span><b>68%</b></div>
          <div className="usage-bar"><i /></div>
          <small>34 de 50 vídeos este mês</small>
          <button className="profile" title={userEmail}>
            <span>{initials}</span><span><b>{displayName}</b><small>Administrador</small></span>
          </button>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <label className="search">
            <span>⌕</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por título ou nicho..."
              aria-label="Buscar conteúdo"
            />
          </label>
          <div className="top-actions">
            <button
              className="notification-button"
              onClick={() => setNotificationsOpen((value) => !value)}
              aria-label={`Notificações: ${unreadCount} não lidas`}
            >
              ♢{unreadCount > 0 && <i>{unreadCount}</i>}
            </button>
            <button className="primary-button" onClick={() => {
              setScheduleTitle(
                approvals.find((item) => item.status === "Aprovado")?.title ?? approvals[0].title,
              );
              setScheduleOpen(true);
            }}>＋ Agendar vídeo</button>
          </div>
          {notificationsOpen && (
            <section className="notification-popover" aria-label="Notificações">
              <header><span><b>Notificações</b><small>{unreadCount} não lidas</small></span>
                <button onClick={() => setNotifications((items) => items.map((item) => ({ ...item, read: true })))}>Marcar lidas</button>
              </header>
              {notifications.map((item) => (
                <button
                  className={item.read ? "notification read" : "notification"}
                  key={item.id}
                  onClick={() => setNotifications((items) => items.map((entry) => entry.id === item.id ? { ...entry, read: true } : entry))}
                >
                  <i className={item.tone} /><span><b>{item.title}</b><small>{item.text}</small></span>
                </button>
              ))}
            </section>
          )}
        </header>

        <div className="content">
          {active === "Aprovações" ? (
            <ApprovalsView
              approvals={filteredApprovals}
              allApprovals={approvals}
              filter={filter}
              setFilter={setFilter}
              openReview={openReview}
            />
          ) : active === "Calendário" ? (
            <CalendarView
              calendar={calendar}
              onSchedule={() => setScheduleOpen(true)}
            />
          ) : active === "Publicações" ? (
            <PublishingView flash={flash} />
          ) : active === "Tendências" ? (
            <TrendsView runtime={runtime} flash={flash} />
          ) : active === "Séries" ? (
            <SeriesView runtime={runtime} flash={flash} />
          ) : active === "Editor visual" || active === "Criar conteúdo" ? (
            <VisualEditorView runtime={runtime} flash={flash} />
          ) : active === "Métricas" ? (
            <MetricsView flash={flash} />
          ) : active === "Experimentos" ? (
            <ExperimentsView flash={flash} />
          ) : active === "Operações" ? (
            <OperationsView flash={flash} runtime={runtime} />
          ) : active === "Release RC1" ? (
            <ReleaseView runtime={runtime} flash={flash} />
          ) : active === "Configurações" ? (
            <AccountSecurityView flash={flash} runtime={runtime} />
          ) : (
            <Overview
              displayName={displayName}
              pendingCount={pendingCount}
              approvals={approvals}
              calendar={calendar}
              openReview={openReview}
              goToApprovals={() => setActive("Aprovações")}
              goToCalendar={() => setActive("Calendário")}
              runtime={runtime}
            />
          )}
        </div>
      </main>

      {selected && (
        <div className="modal-backdrop" onMouseDown={() => setSelected(null)}>
          <section className="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="close-button" aria-label="Fechar revisão" onClick={() => setSelected(null)}>×</button>
            <div className="review-preview">
              <div className="phone-preview">
                <span className="preview-label">{selected.mockPreview ? "PRÉVIA MOCK" : "PRÉVIA"}</span>
                <div className="preview-copy"><small>{selected.niche}</small><b>{selected.hook}</b><span>▶</span></div>
                <div className="caption-sample">PONTES REALMENTE<br /><strong>MUDAM DE TAMANHO</strong></div>
              </div>
              <div className="preview-timeline"><i /><i /><i /><i /></div>
              <small>{selected.duration} · 1080 × 1920 · Legendas incorporadas</small>
            </div>
            <div className="review-content">
              <p className="eyebrow">REVISÃO HUMANA · VERSÃO 1</p>
              <h2 id="review-title">{selected.title}</h2>
              <div className="review-meta"><span>{selected.niche}</span><span>Nota {selected.score}</span><span>{selected.submitted}</span></div>
              <div className="checks">
                <div><span>✓</span><p><b>Moderação concluída</b><small>Nenhuma política bloqueante detectada</small></p></div>
                <div><span>✓</span><p><b>Licenças verificadas</b><small>1 ativo próprio com registro válido</small></p></div>
                <div><span>!</span><p><b>Verificação humana necessária</b><small>Confirme fontes, ritmo e área segura das legendas</small></p></div>
              </div>
              <label className="decision-note">Observação da decisão
                <textarea
                  value={decisionNote}
                  onChange={(event) => setDecisionNote(event.target.value)}
                  placeholder="Obrigatória para reprovar ou solicitar alterações"
                />
              </label>
              <div className="decision-actions">
                <button onClick={() => decide("Reprovado")}>Reprovar</button>
                <button onClick={() => decide("Alterações")}>Solicitar alterações</button>
                <button onClick={() => decide("Aprovado")}>✓ Aprovar vídeo</button>
              </div>
            </div>
          </section>
        </div>
      )}

      {scheduleOpen && (
        <div className="modal-backdrop" onMouseDown={() => setScheduleOpen(false)}>
          <section className="schedule-modal" role="dialog" aria-modal="true" aria-labelledby="schedule-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="close-button" aria-label="Fechar agendamento" onClick={() => setScheduleOpen(false)}>×</button>
            <p className="eyebrow">CALENDÁRIO EDITORIAL</p>
            <h2 id="schedule-title">Reservar horário</h2>
            <p>Somente vídeos aprovados ficam disponíveis. A publicação exige uma conexão TikTok ativa e confirmação explícita.</p>
            <label>Vídeo aprovado
              <select value={scheduleTitle} onChange={(event) => setScheduleTitle(event.target.value)}>
                {approvals.filter((item) => item.status === "Aprovado").map((item) => <option key={item.id}>{item.title}</option>)}
              </select>
            </label>
            <div className="schedule-form-row">
              <label>Dia
                <select value={scheduleDay} onChange={(event) => setScheduleDay(Number(event.target.value))}>
                  {week.map((item) => <option value={item.day} key={item.day}>{item.weekday}, {item.day} JUL</option>)}
                </select>
              </label>
              <label>Horário
                <input type="time" value={scheduleTime} onChange={(event) => setScheduleTime(event.target.value)} />
              </label>
            </div>
            <div className="schedule-safety"><span>✓</span><p><b>Aprovação obrigatória confirmada</b><small>Limite: 5 publicações/dia · intervalo mínimo: 15 minutos</small></p></div>
            <button className="schedule-submit" onClick={addSchedule}>Confirmar reserva</button>
          </section>
        </div>
      )}

      {toast && <div className="toast"><span>✓</span>{toast}</div>}
    </div>
  );
}

function Overview({
  displayName,
  pendingCount,
  approvals,
  calendar,
  openReview,
  goToApprovals,
  goToCalendar,
  runtime,
}: {
  displayName: string;
  pendingCount: number;
  approvals: ApprovalItem[];
  calendar: CalendarItem[];
  openReview: (item: ApprovalItem) => void;
  goToApprovals: () => void;
  goToCalendar: () => void;
  runtime: RuntimeSnapshot;
}) {
  const pending = approvals.filter((item) => item.status === "Pendente").slice(0, 3);
  return (
    <>
      <section className="page-heading">
        <div><p className="eyebrow">CENTRO DE OPERAÇÕES</p><h1>Boa tarde, {displayName}.</h1>
          <p>{runtime.mode === "live" ? "Dados reais sincronizados. " : "Prévia operacional. "}<b>{runtime.dashboard?.awaiting_approval ?? pendingCount} vídeos</b> precisam da sua atenção.</p></div>
        <div className="date-chip"><span>□</span><p><small>SEXTA-FEIRA</small><b>24 JUL, 2026</b></p></div>
      </section>

      <section className="stat-grid">
        <article><span className="metric-icon violet">◉</span><small>PUBLICADOS HOJE</small><strong>{runtime.dashboard?.published_today ?? 3} <i>/ {runtime.dashboard?.daily_limit ?? 5}</i></strong><p>{runtime.mode === "live" ? "Origem: API" : "Próximo às 18:30"}</p></article>
        <article className="attention"><span className="metric-icon amber">✓</span><small>AGUARDANDO APROVAÇÃO</small><strong>{runtime.dashboard?.awaiting_approval ?? pendingCount}</strong><p>Revisão humana obrigatória</p></article>
        <article><span className="metric-icon cyan">◌</span><small>EM PRODUÇÃO</small><strong>{runtime.dashboard?.in_production ?? 7}</strong><p>{runtime.mode === "live" ? "Fila autenticada" : "3 renderizando agora"}</p></article>
        <article><span className="metric-icon pink">□</span><small>AGENDADOS</small><strong>{runtime.dashboard?.scheduled ?? calendar.length}</strong><p>Próximos 7 dias</p></article>
      </section>

      <section className="overview-grid">
        <article className="panel performance-panel">
          <header><span><p className="eyebrow">DESEMPENHO</p><h2>Visão geral</h2></span><small>ÚLTIMOS 7 DIAS</small></header>
          <div className="performance-metrics">
            <p><small>VISUALIZAÇÕES</small><b>482,9K</b><em>↗ 18,4%</em></p>
            <p><small>RETENÇÃO MÉDIA</small><b>68,2%</b><em>↗ 4,1%</em></p>
            <p><small>NOVOS SEGUIDORES</small><b>+2.841</b><em>↗ 21,3%</em></p>
          </div>
          <div className="bar-chart">{[34, 48, 42, 61, 55, 73, 89, 78, 96, 91, 100, 112].map((height, index) => <i style={{ height: `${height / 1.2}%` }} key={index} />)}</div>
        </article>
        <article className="panel opportunity-panel">
          <header><span><p className="eyebrow">INTELIGÊNCIA</p><h2>Oportunidade do dia</h2></span><b>✦</b></header>
          <div className="opportunity"><span><b>94</b><small>POTENCIAL</small></span><p><em>ENGENHARIA</em><b>Por que pontes “respiram”?</b><small>Tema em crescimento e com baixa saturação.</small></p></div>
          <div className="signals"><span><small>CRESCIMENTO</small><b>+184%</b></span><span><small>CONCORRÊNCIA</small><b>Baixa</b></span><span><small>VALIDADE</small><b>~4 dias</b></span></div>
          <button>Preparar nova pauta <span>→</span></button>
        </article>
        <article className="panel approvals-preview">
          <header><span><p className="eyebrow">FLUXO DE TRABALHO</p><h2>Fila de aprovação</h2></span><button onClick={goToApprovals}>Ver todos →</button></header>
          {pending.map((item) => <ApprovalRow item={item} onOpen={() => openReview(item)} key={item.id} />)}
        </article>
        <article className="panel today-panel">
          <header><span><p className="eyebrow">PRÓXIMAS PUBLICAÇÕES</p><h2>Hoje</h2></span><button onClick={goToCalendar}>□</button></header>
          {calendar.filter((item) => item.day === 24).map((item) => (
            <div className="today-item" key={item.id}><time>{item.time}</time><i /><p><b>{item.title}</b><small>{item.niche}</small></p><em>{item.status}</em></div>
          ))}
          <button className="open-calendar" onClick={goToCalendar}>Abrir calendário editorial <span>→</span></button>
        </article>
      </section>
    </>
  );
}

function ReleaseView({ runtime, flash }: { runtime: RuntimeSnapshot; flash: (message: string) => void }) {
  const gates = [
    ["Lint e build", "verified", "Aprovados nesta revisão"],
    ["Renderização SSR", "verified", "Teste de interface aprovado"],
    ["Consistência da release", "verified", "Versão, schema e arquivos conferidos"],
    ["Dependências de produção", "verified", "Auditoria sem vulnerabilidades"],
    ["API e testes", "configured", "Suíte completa configurada no CI"],
    ["Migrações PostgreSQL", "configured", "Cadeia 0001–0009 no RC E2E"],
    ["Jornada autenticada", "configured", "Identidade, 2FA, inteligência e refresh"],
    ["Containers", "configured", "Build e Compose de produção no CI"],
    ["Análise CodeQL", "configured", "Gate de segurança remoto"],
    ["Publicação hospedada", "blocked", "Aguardando identidade da conta Sites"],
  ];
  return (
    <>
      <section className="page-heading release-heading">
        <div><p className="eyebrow">1.0.0-RC.1 · SCHEMA 9</p><h1>Status da release</h1><p>Promoção controlada por evidências da mesma revisão, com rollback compatível para frente.</p></div>
        <span className="release-decision">PROMOÇÃO CONDICIONADA</span>
      </section>
      <section className="release-summary">
        <article><small>GATES LOCAIS</small><b>4 / 4</b><em>VERIFICADOS</em></article>
        <article><small>GATES REMOTOS</small><b>0 / 5</b><em>AGUARDANDO CI</em></article>
        <article><small>SCHEMA</small><b>0009</b><em>ADITIVO</em></article>
        <article><small>AMBIENTE</small><b>{runtime.mode === "live" ? "LIVE" : "PREVIEW"}</b><em>{runtime.mode === "live" ? "API CONECTADA" : "SEM PROMOÇÃO"}</em></article>
      </section>
      <section className="release-layout">
        <article className="panel release-gates">
          <header><span><p className="eyebrow">EVIDÊNCIAS</p><h2>Gates obrigatórios</h2></span><small>MESMA REVISÃO</small></header>
          {gates.map(([name, state, detail]) => <div className={`release-gate ${state}`} key={name}><i>{state === "verified" ? "✓" : state === "blocked" ? "!" : "…"}</i><p><b>{name}</b><small>{detail}</small></p><span>{state === "verified" ? "OK" : state === "blocked" ? "BLOQUEADO" : "CI"}</span></div>)}
        </article>
        <aside className="release-side">
          <article className="panel rollback-card"><p className="eyebrow">ROLLBACK</p><h2>Retorno sem downgrade destrutivo</h2><ol><li>Pausar novas publicações e renders.</li><li>Reativar imagens imutáveis anteriores.</li><li>Preservar schema e corrigir para frente.</li><li>Validar readiness e jornada autenticada.</li></ol><button onClick={() => flash("Plano disponível em docs/RC1-PROMOTION-ROLLBACK.md.")}>Abrir procedimento</button></article>
          <article className="panel external-gates"><p className="eyebrow">INTEGRAÇÕES</p><h2>Condições externas</h2><span>Resend · remetente verificado</span><span>TikTok · aplicativo auditado</span><span>Tendências · fontes contratadas</span><span>Sites · identidade da conta</span></article>
        </aside>
      </section>
      <section className="release-notice"><span>i</span><p><b>RC tecnicamente preparada</b><small>A promoção permanece bloqueada até todos os gates remotos ficarem verdes e as integrações exigidas no ambiente serem validadas.</small></p></section>
    </>
  );
}

function TrendsView({ runtime, flash }: { runtime: RuntimeSnapshot; flash: (message: string) => void }) {
  const seed = [
    { id: "seed-1", topic: "Materiais que se autorreparam", category: "Engenharia", growth_percent: 184, retention_score: 91, share_score: 87, competition: "low", sensitivity_risk: "low", saturation_risk: "low", relevance_reason: "Crescimento consistente em fontes públicas autorizadas.", suggested_approach: "Explicar o mecanismo com uma comparação visual.", likely_audience: "Curiosos por ciência", valid_until: "2026-07-28T23:59:00Z", interest_volume: 12800 },
    { id: "seed-2", topic: "Hábitos de foco profundo", category: "Produtividade", growth_percent: 72, retention_score: 83, share_score: 76, competition: "medium", sensitivity_risk: "low", saturation_risk: "medium", relevance_reason: "Busca crescente por rotinas de concentração.", suggested_approach: "Contrastar mito e prática baseada em evidência.", likely_audience: "Profissionais e estudantes", valid_until: "2026-08-04T23:59:00Z", interest_volume: 9400 },
  ];
  const items = runtime.mode === "live" && runtime.trends?.length ? runtime.trends : seed;
  return (
    <>
      <section className="page-heading"><div><p className="eyebrow">FONTES AUTORIZADAS</p><h1>Descoberta de tendências</h1><p>Sinais importados por API, RSS ou arquivo autorizado — sem scraping incompatível.</p></div><span className="production-badge"><i /> {runtime.mode === "live" ? "DADOS PERSISTIDOS" : "PRÉVIA CONTROLADA"}</span></section>
      <section className="trend-grid">
        {items.map((item) => <article className="panel trend-card" key={item.id}>
          <header><span><small>{item.category}</small><h2>{item.topic}</h2></span><b>+{item.growth_percent}%</b></header>
          <p>{item.relevance_reason}</p>
          <div className="trend-scores"><span><small>RETENÇÃO</small><b>{item.retention_score}</b></span><span><small>COMPART.</small><b>{item.share_score}</b></span><span><small>CONCORRÊNCIA</small><b>{item.competition}</b></span></div>
          <div className="trend-risk"><span>sensibilidade: {item.sensitivity_risk}</span><span>saturação: {item.saturation_risk}</span></div>
          <footer><p><small>ABORDAGEM</small>{item.suggested_approach}</p><button onClick={() => flash(`Pauta “${item.topic}” enviada para criação supervisionada.`)}>Preparar pauta →</button></footer>
        </article>)}
      </section>
    </>
  );
}

function SeriesView({ runtime, flash }: { runtime: RuntimeSnapshot; flash: (message: string) => void }) {
  const seed = [
    { id: "series-1", name: "Engenharia invisível", description: "Mecanismos cotidianos explicados em episódios curtos.", cadence: "weekly", target_episode_count: 12, status: "active", created_at: "" },
    { id: "series-2", name: "Ciência em 40 segundos", description: "Uma pergunta, uma evidência e uma conclusão prática.", cadence: "weekdays", target_episode_count: 20, status: "active", created_at: "" },
  ];
  const items = runtime.mode === "live" && runtime.series?.length ? runtime.series : seed;
  return (
    <>
      <section className="page-heading"><div><p className="eyebrow">CONTINUIDADE EDITORIAL</p><h1>Séries de conteúdo</h1><p>Planeje narrativas recorrentes sem repetir pautas ou automatizar decisões estratégicas.</p></div><button className="primary-button" onClick={() => flash("Criação de série disponível pela API autenticada.")}>＋ Nova série</button></section>
      <section className="series-grid">{items.map((item, index) => <article className="panel series-card" key={item.id}><span className="series-number">0{index + 1}</span><div><small>{item.cadence}</small><h2>{item.name}</h2><p>{item.description}</p></div><footer><span><b>{item.target_episode_count}</b><small>EPISÓDIOS</small></span><em>{item.status === "active" ? "ATIVA" : item.status}</em><button onClick={() => flash(`Série “${item.name}” aberta no planejamento.`)}>Planejar</button></footer></article>)}</section>
    </>
  );
}

function VisualEditorView({ runtime, flash }: { runtime: RuntimeSnapshot; flash: (message: string) => void }) {
  const [projectId, setProjectId] = useState("");
  const [sceneId, setSceneId] = useState("");
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(4200);
  const [transition, setTransition] = useState("fade");
  const [motion, setMotion] = useState("zoom_in");
  const [overlay, setOverlay] = useState("PONTES MUDAM DE TAMANHO");
  async function saveScene() {
    if (runtime.mode !== "live") {
      flash("Prévia atualizada localmente; configure a API para persistir a cena.");
      return;
    }
    const response = await fetch("/api/studio", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: projectId, scene_id: sceneId, start_ms: start, end_ms: end, transition, motion, text_overlay: { text: overlay, safe_area: true } }) });
    flash(response.ok ? "Cena persistida e render marcada para atualização." : "Informe IDs válidos de projeto e cena.");
  }
  return (
    <>
      <section className="page-heading"><div><p className="eyebrow">COMPOSIÇÃO 9:16</p><h1>Editor visual</h1><p>Ajuste tempo, movimento, transição e texto; a API revalida a cena antes do próximo render.</p></div><span className="production-badge"><i /> {runtime.mode === "live" ? "EDIÇÃO PERSISTENTE" : "MODO PRÉVIA"}</span></section>
      <section className="editor-shell panel">
        <div className="editor-preview"><div className={`editor-phone motion-${motion}`}><small>ÁREA SEGURA</small><b>{overlay}</b><span>00:{String(Math.round((end - start) / 1000)).padStart(2, "0")}</span></div></div>
        <div className="editor-controls">
          <label>Projeto<input value={projectId} onChange={(e) => setProjectId(e.target.value)} placeholder="UUID do projeto" /></label>
          <label>Cena<input value={sceneId} onChange={(e) => setSceneId(e.target.value)} placeholder="UUID da cena" /></label>
          <div><label>Início (ms)<input type="number" min="0" value={start} onChange={(e) => setStart(Number(e.target.value))} /></label><label>Fim (ms)<input type="number" min="1" value={end} onChange={(e) => setEnd(Number(e.target.value))} /></label></div>
          <label>Texto na tela<input value={overlay} maxLength={80} onChange={(e) => setOverlay(e.target.value)} /></label>
          <div><label>Transição<select value={transition} onChange={(e) => setTransition(e.target.value)}><option value="cut">Corte</option><option value="fade">Fade</option><option value="dissolve">Dissolver</option></select></label><label>Movimento<select value={motion} onChange={(e) => setMotion(e.target.value)}><option value="none">Nenhum</option><option value="zoom_in">Zoom in</option><option value="zoom_out">Zoom out</option><option value="pan_left">Pan esquerda</option><option value="pan_right">Pan direita</option></select></label></div>
          <div className="editor-safety"><span>✓</span><p><b>Licença preservada</b><small>A troca de mídia continua restrita a ativos licenciados.</small></p></div>
          <button className="primary-button" onClick={saveScene}>Salvar alterações</button>
        </div>
      </section>
    </>
  );
}

function ApprovalsView({
  approvals,
  allApprovals,
  filter,
  setFilter,
  openReview,
}: {
  approvals: ApprovalItem[];
  allApprovals: ApprovalItem[];
  filter: "Todos" | ApprovalStatus;
  setFilter: (value: "Todos" | ApprovalStatus) => void;
  openReview: (item: ApprovalItem) => void;
}) {
  const filters: Array<"Todos" | ApprovalStatus> = ["Todos", "Pendente", "Alterações", "Aprovado", "Reprovado"];
  return (
    <>
      <section className="page-heading approval-heading">
        <div><p className="eyebrow">SUPERVISÃO HUMANA</p><h1>Central de aprovação</h1>
          <p>Revise conteúdo, conformidade e licenças antes de liberar o calendário.</p></div>
        <div className="sla-card"><small>SLA MÉDIO DE REVISÃO</small><b>23 min</b><em>Dentro da meta</em></div>
      </section>
      <section className="workflow-summary">
        <article><small>PENDENTES</small><b>{allApprovals.filter((item) => item.status === "Pendente").length}</b><span>Requer decisão</span></article>
        <article><small>ALTERAÇÕES</small><b>{allApprovals.filter((item) => item.status === "Alterações").length}</b><span>Com a edição</span></article>
        <article><small>APROVADOS</small><b>{allApprovals.filter((item) => item.status === "Aprovado").length}</b><span>Prontos para agenda</span></article>
        <article><small>TAXA DE APROVAÇÃO</small><b>76%</b><span>Últimos 30 dias</span></article>
      </section>
      <section className="panel approval-table-panel">
        <header className="approval-toolbar">
          <div className="filter-tabs">{filters.map((item) => <button className={filter === item ? "active" : ""} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div>
          <small>{approvals.length} resultados</small>
        </header>
        <div className="approval-table-head"><span>CONTEÚDO</span><span>STATUS</span><span>QUALIDADE</span><span>ENVIADO</span><span /></div>
        {approvals.map((item) => <ApprovalRow item={item} onOpen={() => openReview(item)} key={item.id} detailed />)}
        {approvals.length === 0 && <div className="empty-state">Nenhum conteúdo encontrado neste filtro.</div>}
      </section>
    </>
  );
}

function ApprovalRow({ item, onOpen, detailed = false }: { item: ApprovalItem; onOpen: () => void; detailed?: boolean }) {
  return (
    <div className={detailed ? "approval-row detailed" : "approval-row"}>
      <div className={`approval-thumb tone-${item.id}`}><span>▶</span><small>9:16</small></div>
      <div className="approval-copy"><b>{item.title}</b><small>{item.niche} · {item.duration}</small></div>
      <span className={`status-pill status-${item.status.toLocaleLowerCase("pt-BR").replace("ç", "c").replace("õ", "o")}`}><i />{item.status}</span>
      <span className="quality-score"><b>{item.score}</b><small>/100</small></span>
      {detailed && <time>{item.submitted}</time>}
      <button className="review-button" onClick={onOpen}>{item.status === "Pendente" ? "Revisar" : "Abrir"}</button>
    </div>
  );
}

function MetricsView({ flash }: { flash: (message: string) => void }) {
  const [recommendationStatus, setRecommendationStatus] = useState<"open" | "accepted" | "dismissed">("open");
  const bars = [32, 45, 41, 63, 57, 76, 68, 91, 84, 102, 96, 118, 111, 129];
  const retention = [100, 91, 84, 77, 71, 66, 62, 58, 55, 52, 49, 47];
  function decideRecommendation(status: "accepted" | "dismissed") {
    setRecommendationStatus(status);
    flash(status === "accepted" ? "Recomendação aceita para planejamento — nenhuma mudança foi aplicada automaticamente." : "Recomendação arquivada.");
  }
  return (
    <>
      <section className="page-heading metrics-heading">
        <div><p className="eyebrow">APRENDIZADO SUPERVISIONADO</p><h1>Métricas e otimização</h1>
          <p>Compare sinais públicos, retenção importada e decisões editoriais sem prometer desempenho.</p></div>
        <div className="metric-period"><button>7D</button><button className="active">30D</button><button>90D</button></div>
      </section>
      <section className="data-origin-note"><span>DEMO</span><p><b>Dados demonstrativos</b><small>Contagens públicas representam a integração Display API; retenção é exibida como importação do painel do criador.</small></p><button onClick={() => flash("Sincronização simulada concluída.")}>↻ Sincronizar</button></section>
      <section className="analytics-stats">
        <article><small>VISUALIZAÇÕES</small><b>482,9K</b><em>↗ 18,4%</em><span>14 vídeos</span></article>
        <article><small>ENGAJAMENTO</small><b>8,7%</b><em>↗ 1,2 p.p.</em><span>curtidas + comentários + compartilhamentos</span></article>
        <article><small>CONCLUSÃO MÉDIA</small><b>47,2%</b><em>↗ 4,1 p.p.</em><span>fonte: importação manual</span></article>
        <article><small>SEGUIDORES</small><b>28.460</b><em>+2.841</em><span>saldo no período</span></article>
      </section>
      <section className="analytics-layout">
        <article className="panel views-chart">
          <header><span><p className="eyebrow">ALCANCE</p><h2>Visualizações por dia</h2></span><small>482.900 NO PERÍODO</small></header>
          <div className="chart-area">
            <div className="chart-guides"><i /><i /><i /><i /></div>
            <div className="analytics-bars">{bars.map((height, index) => <i key={index} style={{ height: `${height / 1.35}%` }}><span>{Math.round(height * 390)}</span></i>)}</div>
          </div>
          <footer><span>01 JUL</span><span>08 JUL</span><span>15 JUL</span><span>22 JUL</span><span>30 JUL</span></footer>
        </article>
        <article className="panel retention-panel">
          <header><span><p className="eyebrow">RETENÇÃO</p><h2>Curva média</h2></span><em>IMPORTADA</em></header>
          <div className="retention-summary"><p><small>TEMPO MÉDIO</small><b>19,4s</b></p><p><small>ASSISTIRAM ATÉ O FIM</small><b>31,0%</b></p></div>
          <div className="retention-chart">{retention.map((value, index) => <i key={index} style={{ height: `${value}%` }} title={`${index * 3}s · ${value}%`} />)}</div>
          <div className="drop-alert"><span>!</span><p><b>Queda principal aos 6 segundos</b><small>−14 p.p. após a promessa inicial</small></p></div>
        </article>
        <article className="panel content-ranking">
          <header><span><p className="eyebrow">CONTEÚDOS</p><h2>Desempenho comparado</h2></span><button>Exportar CSV</button></header>
          <div className="ranking-head"><span>VÍDEO</span><span>VIEWS</span><span>ENG.</span><span>CONCLUSÃO</span></div>
          {[
            ["O concreto que se regenera", "Engenharia", "84,2K", "10,8%", "58%"],
            ["Por que sentimos déjà vu?", "Ciência", "71,6K", "9,4%", "52%"],
            ["O paradoxo da escolha", "Desenvolvimento", "63,1K", "8,1%", "47%"],
            ["A regra dos 2 minutos", "Produtividade", "48,9K", "6,7%", "39%"],
          ].map((item, index) => <div className="ranking-row" key={item[0]}><span className={`rank-thumb r${index}`}>{index + 1}</span><p><b>{item[0]}</b><small>{item[1]}</small></p><strong>{item[2]}</strong><strong>{item[3]}</strong><strong>{item[4]}</strong></div>)}
        </article>
        <article className="panel recommendation-panel">
          <header><span><p className="eyebrow">RECOMENDAÇÃO</p><h2>Próxima ação sugerida</h2></span><em>81% CONFIANÇA</em></header>
          <div className="recommendation-icon">↗</div>
          <h3>Transforme o formato mais compartilhado em série</h3>
          <p>A proporção de compartilhamentos indica utilidade recorrente. Preserve o tema e varie a entrega para evitar repetição.</p>
          <div className="evidence-chips"><span>Share rate 1,4%</span><span>4 vídeos comparáveis</span><span>Não automático</span></div>
          {recommendationStatus === "open" ? <div className="recommendation-actions"><button onClick={() => decideRecommendation("dismissed")}>Arquivar</button><button onClick={() => decideRecommendation("accepted")}>Aceitar no planejamento</button></div> : <div className="recommendation-decision">✓ {recommendationStatus === "accepted" ? "Aceita para planejamento" : "Arquivada"} · estratégia não alterada automaticamente</div>}
        </article>
      </section>
    </>
  );
}

function ExperimentsView({ flash }: { flash: (message: string) => void }) {
  const [status, setStatus] = useState<"draft" | "running" | "completed">("running");
  const [createOpen, setCreateOpen] = useState(false);
  return (
    <>
      <section className="page-heading experiments-heading">
        <div><p className="eyebrow">TESTES CONTROLADOS · ANTI-SPAM</p><h1>Experimentos</h1>
          <p>Compare duas variantes com uma única diferença e decisão humana sobre o resultado.</p></div>
        <button className="primary-button" onClick={() => setCreateOpen((value) => !value)}>＋ Novo experimento</button>
      </section>
      {createOpen && <section className="experiment-builder">
        <div><small>VARIÁVEL</small><b>Gancho inicial</b></div><div><small>MÉTRICA PRINCIPAL</small><b>Taxa de engajamento</b></div><div><small>REGRA</small><b>2 projetos distintos</b></div>
        <button onClick={() => { setCreateOpen(false); flash("Rascunho de experimento criado."); }}>Criar rascunho</button>
      </section>}
      <section className="experiment-summary">
        <article><small>EM EXECUÇÃO</small><b>{status === "running" ? 1 : 0}</b><span>uma variável por teste</span></article>
        <article><small>CONCLUÍDOS</small><b>{status === "completed" ? 13 : 12}</b><span>últimos 90 dias</span></article>
        <article><small>GANHO MEDIANO</small><b>+8,4%</b><span>sem garantia futura</span></article>
        <article><small>AMOSTRA MÍNIMA</small><b>10K</b><span>views por variante</span></article>
      </section>
      <section className="panel experiment-card">
        <header><span><p className="eyebrow">EXP-014 · GANCHO</p><h2>Explicativo versus direto</h2></span><em className={`experiment-${status}`}>{status === "running" ? "EM EXECUÇÃO" : status === "completed" ? "CONCLUÍDO" : "RASCUNHO"}</em></header>
        <p className="experiment-hypothesis"><b>Hipótese:</b> uma abertura direta aumenta a taxa combinada de interação sem reduzir a conclusão.</p>
        <div className="variant-grid">
          <article><header><span>A</span><small>CONTROLE</small></header><h3>“Você já percebeu por que isso acontece?”</h3><div className="variant-metrics"><p><small>VIEWS</small><b>18,4K</b></p><p><small>ENG.</small><b>7,8%</b></p><p><small>CONCLUSÃO</small><b>46%</b></p></div><i style={{ width: "78%" }} /></article>
          <div className="versus">VS</div>
          <article className="leading"><header><span>B</span><small>LIDERANDO</small></header><h3>“Este erro reduz seu resultado em segundos.”</h3><div className="variant-metrics"><p><small>VIEWS</small><b>19,1K</b></p><p><small>ENG.</small><b>9,2%</b></p><p><small>CONCLUSÃO</small><b>48%</b></p></div><i style={{ width: "92%" }} /></article>
        </div>
        <footer><p><span>i</span><small>Diferença atual: +1,4 p.p. · resultado ainda não aplicado à estratégia.</small></p>{status === "running" ? <button onClick={() => { setStatus("completed"); flash("Experimento concluído. A decisão continua manual."); }}>Encerrar e analisar</button> : <button onClick={() => flash("Variante B registrada como aprendizado editorial.")}>Registrar aprendizado</button>}</footer>
      </section>
      <section className="experiment-safety"><span>✓</span><p><b>Proteção contra conteúdo duplicado</b><small>O DarkTTK exige projetos distintos e uma variável declarada. Publicação e adoção do vencedor continuam dependendo de aprovação.</small></p></section>
    </>
  );
}

function OperationsView({ flash, runtime }: { flash: (message: string) => void; runtime: RuntimeSnapshot }) {
  const [incidentOpen, setIncidentOpen] = useState(true);
  const [budget, setBudget] = useState(Math.round(runtime.costs?.usage_percent ?? 68));
  const [auditVerified, setAuditVerified] = useState(false);
  const live = runtime.mode === "live";
  const readyChecks = runtime.operations ? Object.values(runtime.operations.checks).filter(Boolean).length : 5;
  const totalChecks = runtime.operations ? Object.keys(runtime.operations.checks).length : 6;
  const spent = runtime.costs
    ? new Intl.NumberFormat("pt-BR", { style: "currency", currency: runtime.costs.currency }).format(runtime.costs.spent_cents / 100)
    : "R$ 340";
  const limit = runtime.costs
    ? new Intl.NumberFormat("pt-BR", { style: "currency", currency: runtime.costs.currency }).format(runtime.costs.monthly_limit_cents / 100)
    : "R$ 500";
  const readiness = [
    { label: "API e banco", detail: "Readiness validado", state: "ok" },
    { label: "Filas Redis", detail: "3 workers ativos", state: "ok" },
    { label: "Backup", detail: "Último há 7h · checksum válido", state: "ok" },
    { label: "Publicação", detail: "1 retry sob observação", state: "warn" },
  ];
  return (
    <>
      <section className="page-heading operations-heading">
        <div><p className="eyebrow">FASE 7 · ESCALA E PRODUÇÃO</p><h1>Operações</h1>
          <p>Saúde, segurança, custos e recuperação em uma visão acionável.</p></div>
        <span className={live ? "production-badge live" : "production-badge"}><i /> {live ? "API AUTENTICADA" : runtime.mode === "unavailable" ? "API INDISPONÍVEL" : "AMBIENTE DEMONSTRATIVO"}</span>
      </section>
      <section className="operations-summary">
        <article><small>PRONTIDÃO</small><strong>{readyChecks} / {totalChecks}</strong><span className={readyChecks === totalChecks ? "op-ok" : "op-warn"}>{totalChecks - readyChecks} atenção</span></article>
        <article><small>DISPONIBILIDADE</small><strong>99,97%</strong><span className="op-ok">SLO 99,9%</span></article>
        <article><small>P95 DA API</small><strong>184 ms</strong><span className="op-ok">−21 ms</span></article>
        <article><small>CUSTO DO MÊS</small><strong>{spent}</strong><span>de {limit}</span></article>
      </section>
      <section className="operations-grid">
        <article className="panel readiness-panel">
          <header><span><p className="eyebrow">READINESS</p><h2>Serviços essenciais</h2></span><em className={runtime.operations?.status === "ready" ? "status-ok" : "status-attention"}>{runtime.operations?.status === "ready" ? "PRONTO" : "ATENÇÃO"}</em></header>
          <div className="service-list">
            {readiness.map((item) => <div key={item.label}><i className={item.state} /><p><b>{item.label}</b><small>{item.detail}</small></p><span>{item.state === "ok" ? "OPERACIONAL" : "OBSERVAR"}</span></div>)}
          </div>
          <footer><small>{runtime.message}</small><button onClick={() => flash("A página será atualizada para executar novos checks.")}>Executar checks</button></footer>
        </article>
        <article className="panel cost-panel">
          <header><span><p className="eyebrow">FINOPS</p><h2>Orçamento mensal</h2></span><b>{budget}%</b></header>
          <div className="cost-ring" style={{ "--cost": `${budget * 3.6}deg` } as React.CSSProperties}><span><b>{spent}</b><small>consumidos</small></span></div>
          <div className="budget-bar"><i style={{ width: `${budget}%` }} /></div>
          <p><span>Alerta preventivo</span><b>{runtime.costs?.warning_percent ?? 80}%</b></p>
          <input aria-label="Simular uso do orçamento" type="range" min="0" max="100" value={budget} disabled={live} onChange={(event) => setBudget(Number(event.target.value))} />
          <small>{live ? "Valor carregado do ledger real; alterações exigem perfil gestor." : "Simulação local; alterações reais exigem API configurada."}</small>
        </article>
        <article className="panel incident-panel">
          <header><span><p className="eyebrow">INCIDENTES</p><h2>Fila operacional</h2></span><em>{incidentOpen ? "1 ABERTO" : "0 ABERTOS"}</em></header>
          {incidentOpen && (runtime.operations?.open_errors ?? 1) > 0 ? <div className="incident-item"><span>!</span><p><b>Incidente operacional requer análise</b><small>{runtime.operations?.open_errors ?? 1} erro(s) aberto(s) · {runtime.operations?.failed_publications ?? 1} publicação(ões) falha(s)</small><code>operations_attention</code></p></div>
            : <div className="empty-incident">✓ Nenhum incidente operacional aberto.</div>}
          <div className="incident-actions"><button onClick={() => flash("Runbook de publicação aberto.")}>Abrir runbook</button><button onClick={() => { setIncidentOpen(false); flash("Incidente reconhecido; a resolução exige ação corretiva."); }}>Reconhecer</button></div>
        </article>
        <article className="panel security-panel">
          <header><span><p className="eyebrow">SEGURANÇA</p><h2>Controles ativos</h2></span><em>7 / 7</em></header>
          <div className="security-checks">
            <span>✓ Rate limit distribuído</span><span>✓ Segredos fora do código</span>
            <span>✓ Tokens criptografados</span><span>✓ Cabeçalhos restritivos</span>
            <span>✓ RBAC por organização</span><span>✓ Payload limitado</span>
            <span>✓ Auditoria com checkpoint</span>
          </div>
          <button onClick={() => flash("Relatório de segurança preparado para exportação.")}>Exportar evidências</button>
        </article>
        <article className="panel backup-panel">
          <header><span><p className="eyebrow">RECUPERAÇÃO</p><h2>Backup e restore</h2></span><em className="status-ok">VERIFICADO</em></header>
          <div className="backup-timeline"><i /><p><b>Banco PostgreSQL</b><small>02:00 · 148 MB · SHA-256 conferido</small></p><span>7h</span></div>
          <div className="backup-timeline"><i /><p><b>Objetos de mídia</b><small>02:15 · incremental · retenção 30 dias</small></p><span>7h</span></div>
          <div className="restore-objective"><span><small>RPO</small><b>24 h</b></span><span><small>RTO</small><b>2 h</b></span><span><small>ÚLTIMO TESTE</small><b>18 jul</b></span></div>
          <button onClick={() => flash("Restore de teste deve ser executado em ambiente isolado.")}>Ver plano de recuperação</button>
        </article>
        <article className="panel audit-panel">
          <header><span><p className="eyebrow">AUDITORIA</p><h2>Integridade da trilha</h2></span><em className={auditVerified ? "status-ok" : ""}>{auditVerified ? "ÍNTEGRA" : "PENDENTE"}</em></header>
          <div className="audit-hash"><small>CHECKPOINT MAIS RECENTE</small><code>7a4f21b9…e88c</code><span>1.284 eventos</span></div>
          <p>O checkpoint preserva ordem, conteúdo e contagem dos eventos por SHA-256.</p>
          <button onClick={() => { setAuditVerified(true); flash("Checkpoint conferido sem divergências."); }}>{auditVerified ? "Verificado agora" : "Verificar checkpoint"}</button>
        </article>
      </section>
      <section className="production-note"><span>i</span><p><b>{live ? "Origem autenticada" : "Prévia segura"}</b><small>{runtime.message} Valores sem origem real permanecem identificados como demonstração.</small></p></section>
    </>
  );
}

function AccountSecurityView({ flash, runtime }: { flash: (message: string) => void; runtime: RuntimeSnapshot }) {
  const [enabled, setEnabled] = useState(false);
  const [remaining, setRemaining] = useState(0);
  const [setup, setSetup] = useState<{ secret: string; provisioning_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const live = runtime.mode === "live";

  useEffect(() => {
    if (!live) return;
    void fetch("/api/account/security")
      .then((response) => response.ok ? response.json() : null)
      .then((status: { enabled: boolean; recovery_codes_remaining: number } | null) => {
        if (status) {
          setEnabled(status.enabled);
          setRemaining(status.recovery_codes_remaining);
        }
      });
  }, [live]);

  async function startSetup() {
    const response = await fetch("/api/account/security", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "setup" }),
    });
    if (!response.ok) {
      flash("Não foi possível iniciar o 2FA.");
      return;
    }
    setSetup(await response.json());
    setRecoveryCodes([]);
    flash("Segredo TOTP criado. Confirme com o código do autenticador.");
  }

  async function confirmSetup() {
    const response = await fetch("/api/account/security", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "confirm", code }),
    });
    if (!response.ok) {
      flash("Código inválido ou já utilizado.");
      return;
    }
    const result = await response.json() as { enabled: boolean; recovery_codes: string[] };
    setEnabled(result.enabled);
    setRemaining(result.recovery_codes.length);
    setRecoveryCodes(result.recovery_codes);
    setSetup(null);
    setCode("");
    flash("2FA ativado para o login por senha.");
  }

  async function regenerateCodes() {
    const response = await fetch("/api/account/security", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "regenerate", code }),
    });
    if (!response.ok) {
      flash("Confirme com um TOTP válido para renovar os códigos.");
      return;
    }
    const result = await response.json() as { enabled: boolean; recovery_codes: string[] };
    setRemaining(result.recovery_codes.length);
    setRecoveryCodes(result.recovery_codes);
    setCode("");
    flash("Códigos anteriores revogados; guarde os novos agora.");
  }

  return (
    <>
      <section className="page-heading">
        <div><p className="eyebrow">CONTA E PROTEÇÃO</p><h1>Segurança</h1>
          <p>Controle o segundo fator, recuperação de conta e sessões da API.</p></div>
        <span className={live ? "production-badge live" : "production-badge"}><i /> {live ? "API AUTENTICADA" : "CONFIGURAÇÃO NECESSÁRIA"}</span>
      </section>
      <section className="security-settings-grid">
        <article className="panel mfa-settings">
          <header><span><p className="eyebrow">AUTENTICAÇÃO</p><h2>Aplicativo autenticador</h2></span><em className={enabled ? "status-ok" : ""}>{enabled ? "ATIVO" : "INATIVO"}</em></header>
          <p>O TOTP protege o login por e-mail e senha. O acesso pelo workspace continua usando a identidade autenticada da plataforma.</p>
          {setup && <div className="mfa-setup-box">
            <small>CHAVE MANUAL</small><code>{setup.secret}</code>
            <small>URI DE PROVISIONAMENTO</small><code className="uri">{setup.provisioning_uri}</code>
            <label>Código de 6 dígitos<input inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value)} placeholder="000000" /></label>
            <button onClick={confirmSetup}>Confirmar e ativar</button>
          </div>}
          {!setup && <button disabled={!live || enabled} onClick={startSetup}>{enabled ? "2FA já configurado" : "Configurar 2FA"}</button>}
          {enabled && <>
            <small className="security-footnote">{remaining} códigos de recuperação disponíveis.</small>
            <div className="mfa-regenerate">
              <label>TOTP atual<input inputMode="numeric" value={code} onChange={(event) => setCode(event.target.value)} placeholder="000000" /></label>
              <button onClick={regenerateCodes}>Renovar códigos</button>
            </div>
          </>}
        </article>
        <article className="panel recovery-settings">
          <header><span><p className="eyebrow">RECUPERAÇÃO</p><h2>Redefinição de senha</h2></span><em>PROTEGIDO</em></header>
          <div className="security-feature"><span>✓</span><p><b>Token de uso único</b><small>Armazenado somente por hash e válido por 30 minutos.</small></p></div>
          <div className="security-feature"><span>✓</span><p><b>Revogação de sessões</b><small>Todos os refresh tokens são invalidados após a troca.</small></p></div>
          <div className="security-feature"><span>✓</span><p><b>Canal de entrega</b><small>Adaptador Resend disponível; o modo permanece desativado até as credenciais serem configuradas.</small></p></div>
        </article>
      </section>
      {recoveryCodes.length > 0 && <section className="panel recovery-code-panel">
        <header><span><p className="eyebrow">EXIBIÇÃO ÚNICA</p><h2>Códigos de recuperação</h2></span><em>GUARDE AGORA</em></header>
        <p>Estes códigos não serão exibidos novamente. Cada código funciona uma única vez.</p>
        <div>{recoveryCodes.map((item) => <code key={item}>{item}</code>)}</div>
      </section>}
    </>
  );
}

function PublishingView({ flash }: { flash: (message: string) => void }) {
  const [connected, setConnected] = useState(false);
  const [creatorReady, setCreatorReady] = useState(false);
  const [privacy, setPrivacy] = useState("");
  const [comment, setComment] = useState("");
  const [duet, setDuet] = useState("");
  const [stitch, setStitch] = useState("");
  const [brandContent, setBrandContent] = useState(false);
  const [brandOrganic, setBrandOrganic] = useState(false);
  const [aigc, setAigc] = useState(true);
  const [consent, setConsent] = useState(false);
  const [musicConfirmed, setMusicConfirmed] = useState(false);
  const [caption, setCaption] = useState("Mais escolhas nem sempre levam a decisões melhores. #psicologia #curiosidades");
  const [jobStatus, setJobStatus] = useState<"idle" | "processing" | "mock_complete">("idle");
  const brandedPrivateConflict = brandContent && privacy === "SELF_ONLY";
  const ready =
    connected &&
    creatorReady &&
    Boolean(privacy && comment && duet && stitch) &&
    consent &&
    musicConfirmed &&
    !brandedPrivateConflict;

  function simulateConnection() {
    setConnected(true);
    setCreatorReady(false);
    flash("Conexão simulada. Nenhuma conta real foi acessada.");
  }

  function refreshCreatorInfo() {
    setCreatorReady(true);
    setPrivacy("");
    setComment("");
    setDuet("");
    setStitch("");
    flash("Opções da conta simulada atualizadas.");
  }

  function simulatePublication() {
    if (!ready) {
      flash("Revise todos os campos e confirme o envio.");
      return;
    }
    setJobStatus("processing");
    window.setTimeout(() => {
      setJobStatus("mock_complete");
      flash("Simulação concluída — nenhuma publicação real foi criada.");
    }, 900);
  }

  return (
    <>
      <section className="page-heading publishing-heading">
        <div>
          <p className="eyebrow">CONTENT POSTING API · CONTROLE HUMANO</p>
          <h1>Central de publicações</h1>
          <p>Conecte a conta, revise as opções retornadas pelo TikTok e autorize cada envio.</p>
        </div>
        <span className="demo-badge">AMBIENTE DE DEMONSTRAÇÃO</span>
      </section>

      <section className="connection-card">
        <div className="tiktok-mark">♪</div>
        <div>
          <small>CONEXÃO TIKTOK</small>
          <b>{connected ? "@darkttk_mock" : "Nenhuma conta conectada"}</b>
          <span className={connected ? "connection-ok" : ""}>
            <i /> {connected ? "Simulação ativa · tokens protegidos no servidor" : "Publicação real desativada"}
          </span>
        </div>
        {connected ? (
          <button onClick={() => { setConnected(false); setCreatorReady(false); }}>Desconectar</button>
        ) : (
          <button className="connect-button" onClick={simulateConnection}>Simular conexão segura</button>
        )}
      </section>

      <section className="publishing-grid">
        <article className="panel publish-composer">
          <header>
            <span><p className="eyebrow">AUTORIZAÇÃO DE ENVIO</p><h2>O paradoxo da escolha</h2></span>
            <em>24 JUL · 18:30</em>
          </header>

          <div className="creator-refresh">
            <span className={creatorReady ? "ready" : ""}>{creatorReady ? "✓" : "1"}</span>
            <p><b>Consultar opções da conta</b><small>Privacidade e interações não recebem valores padrão.</small></p>
            <button disabled={!connected} onClick={refreshCreatorInfo}>{creatorReady ? "Atualizar" : "Consultar agora"}</button>
          </div>

          <label className="publish-field">Legenda
            <textarea value={caption} onChange={(event) => setCaption(event.target.value)} maxLength={2200} />
            <small>{caption.length}/2.200</small>
          </label>

          <div className="publish-fields">
            <label>Privacidade
              <select value={privacy} disabled={!creatorReady} onChange={(event) => setPrivacy(event.target.value)}>
                <option value="">Selecione manualmente</option>
                <option value="PUBLIC_TO_EVERYONE">Público</option>
                <option value="MUTUAL_FOLLOW_FRIENDS">Amigos</option>
                <option value="SELF_ONLY">Somente eu</option>
              </select>
            </label>
            {[
              ["Comentários", comment, setComment],
              ["Dueto", duet, setDuet],
              ["Costura", stitch, setStitch],
            ].map(([label, value, setter]) => (
              <label key={label as string}>{label as string}
                <select
                  value={value as string}
                  disabled={!creatorReady}
                  onChange={(event) => (setter as (value: string) => void)(event.target.value)}
                >
                  <option value="">Selecione</option>
                  <option value="allow">Permitir</option>
                  <option value="block">Bloquear</option>
                </select>
              </label>
            ))}
          </div>

          <div className="disclosure-box">
            <p><b>Divulgação e origem</b><small>Informe conteúdo comercial e mídia gerada por IA.</small></p>
            <label><input type="checkbox" checked={brandContent} onChange={(event) => setBrandContent(event.target.checked)} /> Conteúdo de marca</label>
            <label><input type="checkbox" checked={brandOrganic} onChange={(event) => setBrandOrganic(event.target.checked)} /> Promove minha marca</label>
            <label><input type="checkbox" checked={aigc} onChange={(event) => setAigc(event.target.checked)} /> Conteúdo gerado por IA</label>
            {brandedPrivateConflict && <strong>Conteúdo de marca não pode ser enviado como “Somente eu”.</strong>}
          </div>

          <div className="consent-box">
            <label><input type="checkbox" checked={musicConfirmed} onChange={(event) => setMusicConfirmed(event.target.checked)} /> Confirmo que possuo os direitos de uso da música e dos ativos.</label>
            <label><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> Autorizo expressamente este envio para a conta selecionada.</label>
          </div>
          <button className="publish-submit" disabled={!ready || jobStatus === "processing"} onClick={simulatePublication}>
            {jobStatus === "processing" ? "Enviando para a fila…" : "Autorizar publicação"}
          </button>
          <small className="publish-disclaimer">Esta tela está em modo demonstrativo. O fluxo oficial só é ativado com credenciais e aprovação do aplicativo TikTok.</small>
        </article>

        <aside className="publication-side">
          <article className="panel publish-preview-card">
            <header><span><p className="eyebrow">PRÉVIA</p><h2>Como aparecerá</h2></span><em>9:16</em></header>
            <div className="mini-phone"><b>MAIS ESCOLHAS<br /><strong>NEM SEMPRE AJUDAM</strong></b><span>PRÉVIA MOCK</span></div>
            <p>{caption}</p>
            <div><span>{privacy || "Privacidade pendente"}</span><span>{aigc ? "IA sinalizada" : "IA não sinalizada"}</span></div>
          </article>
          <article className="panel job-card">
            <header><span><p className="eyebrow">FILA E CONFIRMAÇÃO</p><h2>Status do envio</h2></span></header>
            <div className={jobStatus === "idle" ? "job-step current" : "job-step done"}><i /> <p><b>Autorização humana</b><small>{jobStatus === "idle" ? "Aguardando confirmação" : "Registrada com data e usuário"}</small></p></div>
            <div className={jobStatus === "processing" ? "job-step current" : jobStatus === "mock_complete" ? "job-step done" : "job-step"}><i /> <p><b>Processamento</b><small>Fila isolada com repetição controlada</small></p></div>
            <div className={jobStatus === "mock_complete" ? "job-step mock" : "job-step"}><i /> <p><b>Confirmação do provedor</b><small>{jobStatus === "mock_complete" ? "Simulação concluída; não publicado" : "Aguardando webhook ou consulta de status"}</small></p></div>
          </article>
        </aside>
      </section>
    </>
  );
}

function CalendarView({ calendar, onSchedule }: { calendar: CalendarItem[]; onSchedule: () => void }) {
  return (
    <>
      <section className="page-heading calendar-heading">
        <div><p className="eyebrow">PLANEJAMENTO EDITORIAL</p><h1>Calendário</h1>
          <p>Organize até cinco publicações por dia sem sobreposição de horários.</p></div>
        <button className="primary-button" onClick={onSchedule}>＋ Reservar horário</button>
      </section>
      <section className="calendar-toolbar">
        <button>←</button><div><small>SEMANA 30</small><b>24–30 de julho de 2026</b></div><button>→</button>
        <span><i /> Pronto <i /> Reservado</span>
      </section>
      <section className="week-grid">
        {week.map((day) => {
          const items = calendar.filter((item) => item.day === day.day).sort((a, b) => a.time.localeCompare(b.time));
          return (
            <article className={day.day === 24 ? "today" : ""} key={day.day}>
              <header><small>{day.weekday}</small><b>{day.day}</b><em>{items.length}/5</em></header>
              <div className="day-slots">
                {items.map((item) => (
                  <div className={item.status === "Pronto" ? "calendar-card ready" : "calendar-card"} key={item.id}>
                    <time>{item.time}</time><b>{item.title}</b><small>{item.niche}</small><span>{item.status}</span>
                  </div>
                ))}
                {items.length === 0 && <button className="empty-slot" onClick={onSchedule}>＋ Adicionar</button>}
              </div>
            </article>
          );
        })}
      </section>
      <section className="calendar-footnote"><span>i</span><p><b>Publicação exige autorização</b><small>Abra a Central de publicações para escolher a conta, revisar a privacidade e consentir com o envio.</small></p></section>
    </>
  );
}
