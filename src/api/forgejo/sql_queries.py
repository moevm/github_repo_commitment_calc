GET_FULL_PR_INFO = """
SELECT
    r.owner_name || '/' || r.name                                   AS repository_name,
    i.name                                                          AS title,
    i.index                                                         AS number,
    i.num_comments                                                  AS num_comments,
    CASE WHEN i.is_closed THEN 'closed' ELSE 'open' END             AS state,
    pr.base_branch                                                  AS commit_into,
    pr.head_branch                                                  AS commit_from,
    to_timestamp(i.created_unix)                                    AS created_at,
    creator.name                                                    AS creator_name,
    creator.lower_name                                              AS creator_login,
    creator.email                                                   AS creator_email,
    NULL::text                                                      AS changed_files,
    (SELECT string_agg(c.content, E'\\n---\\n' ORDER BY c.created_unix)
       FROM comment c WHERE c.issue_id = i.id)                      AS comment_body,
    (SELECT string_agg(to_timestamp(c.created_unix)::text, ', ' ORDER BY c.created_unix)
       FROM comment c WHERE c.issue_id = i.id)                      AS comment_created_at,
    (SELECT string_agg(cu.name, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id)                                      AS comment_author_name,
    (SELECT string_agg(cu.lower_name, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id)                                      AS comment_author_login,
    (SELECT string_agg(cu.email, ', ' ORDER BY c.created_unix)
       FROM comment c JOIN "user" cu ON c.poster_id = cu.id
      WHERE c.issue_id = i.id)                                      AS comment_author_email,
    merger.name                                                     AS merger_name,
    merger.lower_name                                               AS merger_login,
    merger.email                                                    AS merger_email,
    pr.head_branch                                                  AS source_branch,
    pr.base_branch                                                  AS target_branch,
    (SELECT string_agg(a.name, ', ' ORDER BY a.name)
       FROM issue_assignees ia JOIN "user" a ON ia.assignee_id = a.id
      WHERE ia.issue_id = i.id)                                     AS assignee_story,
    (SELECT string_agg(related_id::text, ', ' ORDER BY related_id)
       FROM (
           SELECT dependency_id AS related_id
             FROM issue_dependency WHERE issue_id = i.id
           UNION
           SELECT issue_id AS related_id
             FROM issue_dependency WHERE dependency_id = i.id
       ) AS rel)                                                    AS related_issues,
    (SELECT string_agg(l.name, ', ' ORDER BY l.name)
       FROM issue_label il JOIN label l ON il.label_id = l.id
      WHERE il.issue_id = i.id)                                     AS labels,
    m.name                                                          AS milestone,
    pr.has_merged                                                   AS merged
FROM pull_request pr
INNER JOIN issue i         ON pr.issue_id     = i.id
INNER JOIN repository r    ON pr.base_repo_id = r.id
INNER JOIN "user" creator  ON i.poster_id     = creator.id
LEFT  JOIN "user" merger   ON pr.merger_id    = merger.id
LEFT  JOIN milestone m     ON i.milestone_id  = m.id
WHERE r.owner_name || '/' || r.name = ANY(%s)
ORDER BY i.created_unix DESC;
"""