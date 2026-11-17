GET_FULL_PR_INFO = """
SELECT
    i.id                                                            AS issue_id,
    -- Репозиторий
    r.owner_name || '/' || r.name                                   AS repository_name,

    -- Основные поля PR (для PullRequest)
    i.index                                                         AS number,
    i.name                                                          AS title,
    CASE WHEN i.is_closed THEN 'closed' ELSE 'open' END             AS state,
    to_timestamp(i.created_unix)                                    AS created_at,
    pr.head_branch                                                  AS source_branch,
    pr.base_branch                                                  AS target_branch,
    pr.has_merged                                                   AS merged,
    i.num_comments                                                  AS num_comments,
    m.name                                                          AS milestone,

    -- Автор PR (для User)
    creator.id                                                      AS creator_id,
    creator.name                                                    AS creator_name,
    creator.lower_name                                              AS creator_login,
    creator.full_name                                               AS creator_full_name,
    creator.email                                                   AS creator_email,
    creator.description                                             AS creator_bio,
    creator.is_admin                                                AS creator_is_admin,
    creator.type                                                    AS creator_type,

    -- Мержер (для User)
    merger.id                                                       AS merger_id,
    merger.name                                                     AS merger_name,
    merger.lower_name                                               AS merger_login,
    merger.full_name                                                AS merger_full_name,
    merger.email                                                    AS merger_email,
    merger.description                                              AS merger_bio,
    merger.is_admin                                                 AS merger_is_admin,
    merger.type                                                     AS merger_type,

    -- Лейблы
    (SELECT string_agg(l.name, ', ' ORDER BY l.name)
       FROM issue_label il JOIN label l ON il.label_id = l.id
      WHERE il.issue_id = i.id)                                     AS labels

FROM pull_request pr
INNER JOIN issue i         ON pr.issue_id     = i.id
INNER JOIN repository r    ON pr.base_repo_id = r.id
INNER JOIN "user" creator  ON i.poster_id     = creator.id
LEFT  JOIN "user" merger   ON pr.merger_id    = merger.id
LEFT  JOIN milestone m     ON i.milestone_id  = m.id
WHERE (
    %(repo_name_contains)s::text[] IS NULL
    OR EXISTS (
        SELECT 1
        FROM unnest(%(repo_name_contains)s::text[]) AS filter(name_part)
        WHERE strpos(lower(r.name), lower(filter.name_part)) > 0
    )
)
AND (%(organization)s IS NULL OR lower(r.owner_name) = lower(%(organization)s))
ORDER BY i.created_unix DESC;
"""

GET_USER_BY_ID = """
SELECT id, name, lower_name, full_name, email, description, is_admin, type
  FROM "user" WHERE id = %s;
"""

GET_PR_COMMENTS = """
SELECT
    c.issue_id,
    c.content AS body,
    to_timestamp(c.created_unix) AS created_at,
    COALESCE(u.id, -1) AS author_id,
    COALESCE(u.name, 'Ghost') AS author_name,
    COALESCE(u.lower_name, 'ghost') AS author_login,
    u.full_name AS author_full_name,
    u.email AS author_email,
    u.description AS author_bio,
    u.is_admin AS author_is_admin,
    u.type AS author_type
FROM comment c
LEFT JOIN "user" u ON c.poster_id = u.id
LEFT JOIN review rv ON c.review_id = rv.id AND rv.issue_id = c.issue_id
WHERE c.issue_id = ANY(%s)
  AND (
      c.type = 0
      OR (c.type IN (21, 22) AND rv.type IN (1, 2, 3)
          AND (c.type = 21 OR btrim(c.content) <> ''))
  )
ORDER BY c.issue_id, c.created_unix, c.id;
"""

GET_REPO = """
SELECT
    r.id,
    r.owner_name,
    r.name,
    r.lower_name,
    r.description,
    r.default_branch,
    r.owner_id,
    u.id            AS owner_id,
    u.name          AS owner_name_user,
    u.lower_name    AS owner_login,
    u.full_name     AS owner_full_name,
    u.email         AS owner_email,
    u.description   AS owner_description,
    u.is_admin      AS owner_is_admin,
    u.type          AS owner_type
FROM repository r
LEFT JOIN "user" u ON r.owner_id = u.id
WHERE r.owner_name || '/' || r.name = %s;
"""
