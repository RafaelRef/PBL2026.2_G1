    -- esquema.sql -- tabelas do BabyCare Hemo no Supabase.
    --
    -- COMO RODAR: painel do Supabase -> SQL Editor -> New query -> cole tudo
    -- isto -> Run. Pode rodar de novo sem medo: tudo e' "if not exists".
    --
    -- Substitui o dados_clinicos.json local. O arquivo continua funcionando
    -- quando SUPABASE_URL nao esta definido, para desenvolver sem internet.

    -- ---------------------------------------------------------------- medicos
    create table if not exists public.usuarios (
        login      text primary key,
        salt       text        not null,
        hash       text        not null,   -- PBKDF2-SHA256; senha nunca em texto
        nome       text        not null,
        criado_em  timestamptz not null default now()
    );

    -- ---------------------------------------------------------------- bebes
    create table if not exists public.pacientes (
        id             bigint generated always as identity primary key,
        nome           text             not null,
        peso           double precision not null,   -- kg, no dia do cadastro
        semana_vida    double precision not null,   -- idade pos-natal no cadastro
        cadastrado_por text             not null references public.usuarios(login),
        cadastrado_em  timestamptz      not null default now()
    );

    -- ---------------------------------------------------------------- puncoes
    create table if not exists public.coletas (
        id          bigint generated always as identity primary key,
        paciente_id bigint           not null
                    references public.pacientes(id) on delete cascade,
        exame       text             not null,   -- gasometria | hemograma | glicemia
        volume      double precision not null,   -- mL
        hora_vida   double precision not null,   -- h desde o nascimento
        em          timestamptz      not null default now()
    );

    create index if not exists coletas_por_paciente
    on public.coletas (paciente_id);

    -- ---------------------------------------------------------------- seguranca
    -- RLS ligado e NENHUMA politica criada: nega tudo por padrao.
    --
    -- A chave publica (anon / publishable) aparece em qualquer navegador, entao
    -- sem isto qualquer pessoa leria a lista de pacientes. Nosso servidor usa a
    -- chave SECRETA (service_role), que ignora RLS de proposito -- por isso ele
    -- continua funcionando e mais ninguem consegue ler nada.
    alter table public.usuarios  enable row level security;
    alter table public.pacientes enable row level security;
    alter table public.coletas   enable row level security;

    -- ---------------------------------------------------------------- transfusoes
    -- Transfusoes que o MEDICO aceitou. O modelo nao transfunde sozinho na
    -- interface (simular roda com transfundir=False): cada linha aqui e' uma
    -- decisao registrada, e entra na simulacao pela agenda_transfusoes.
    create table if not exists public.transfusoes (
    id          bigint generated always as identity primary key,
    paciente_id bigint           not null
                references public.pacientes(id) on delete cascade,
    volume      double precision not null,   -- mL de concentrado
    hct_antes   double precision not null,   -- Hct no momento da decisao
    hora_vida   double precision not null,   -- h desde o nascimento
    decidida_por text            not null references public.usuarios(login),
    em          timestamptz      not null default now()
    );

    create index if not exists transfusoes_por_paciente
    on public.transfusoes (paciente_id);

    alter table public.transfusoes enable row level security;

    -- ---------------------------------------------------------------- migracao
    -- Para bancos criados antes da coleta forcada. Uma coleta "forcada" e' a que
    -- o medico registrou sabendo que furava uma das regras -- exame de urgencia.
    -- Fica marcada para o registro mostrar que a decisao foi consciente.
    alter table public.coletas
    add column if not exists forcada boolean not null default false;

    -- ---------------------------------------------------------------- demonstracao
    -- Avanco manual do tempo, em dias. Numa UTI de verdade quem anda e' o
    -- calendario; isto existe para a apresentacao, onde ninguem espera duas
    -- semanas para ver o hematocrito cair. Soma-se a idade real do paciente.
    alter table public.pacientes
    add column if not exists dias_extra double precision not null default 0;
