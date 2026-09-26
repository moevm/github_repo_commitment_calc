GET_FULL_PR_INFO = """
SELECT
    -- Репозиторий
    r.owner_name || '/' || r.name                                   AS repository_name,

    -- Основные поля PR (для PullRequest)
    i.index                                                         AS number,
    i.name                                                          AS title,
    CASE WHEN i.is_closed THEN 'closed' ELSE 'open' END             AS state,
    to_timestamp(i.created_unix)                                    AS created_at,
    pr.head_branch                                                  AS source_branch,
    pr.base_branch                                                  AS target_branch,
    pr.head_branch                                                  AS head_ref,
    pr.base_branch                                                  AS base_ref,
    pr.has_merged                                                   AS merged,
    i.num_comments                                                  AS num_comments,
    0                                                               AS review_comments,
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
      WHERE il.issue_id = i.id)                                     AS labels,

    -- Назначенные исполнители
    (SELECT string_agg(a.name, ', ' ORDER BY a.name)
       FROM issue_assignees ia JOIN "user" a ON ia.assignee_id = a.id
      WHERE ia.issue_id = i.id)                                     AS assignee_story,

    -- Связанные issues
    (SELECT string_agg(related_id::text, ', ' ORDER BY related_id)
       FROM (
           SELECT dependency_id AS related_id
             FROM issue_dependency WHERE issue_id = i.id
           UNION
           SELECT issue_id AS related_id
             FROM issue_dependency WHERE dependency_id = i.id
       ) AS rel)                                                    AS related_issues,

    -- Комментарии (только пользовательские, type = 0)
    (SELECT string_agg(c.content, E'\n---\n' ORDER BY c.created_unix)
       FROM comment c
      WHERE c.issue_id = i.id AND c.type = 0)                       AS comment_body,
    (SELECT string_agg(to_timestamp(c.created_unix)::text, ', ' ORDER BY c.created_unix)
       FROM comment c
      WHERE c.issue_id = i.id AND c.type = 0)                       AS comment_created_at,
    (SELECT string_agg(cu.name, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id AND c.type = 0)                       AS comment_author_name,
    (SELECT string_agg(cu.lower_name, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id AND c.type = 0)                       AS comment_author_login,
    (SELECT string_agg(cu.email, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id AND c.type = 0)                       AS comment_author_email,

    -- Изменённые файлы (через БД недоступны)
    NULL::text                                                      AS changed_files

FROM pull_request pr
INNER JOIN issue i         ON pr.issue_id     = i.id
INNER JOIN repository r    ON pr.base_repo_id = r.id
INNER JOIN "user" creator  ON i.poster_id     = creator.id
LEFT  JOIN "user" merger   ON pr.merger_id    = merger.id
LEFT  JOIN milestone m     ON i.milestone_id  = m.id
ORDER BY i.created_unix DESC;
"""

GET_USER_BY_ID = """
SELECT id, name, lower_name, full_name, email, description, is_admin, type
  FROM "user" WHERE id = %s;
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