param(
    [string]$BaseUrl = "http://127.0.0.1:8000/api",
    [string]$MysqlExe = "F:\mysql-8.0.44-winx64\bin\mysql.exe",
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3306,
    [string]$DbName = "blog_platform",
    [string]$DbUser = "root",
    [string]$DbPassword = "root",
    [string]$DemoUsername = "paper_demo_user",
    [string]$DemoEmail = "paper_demo_user@example.com",
    [string]$DemoPassword = "123456",
    [string]$PreferenceTags = "ai,recommendation,analytics,frontend"
)

$ErrorActionPreference = "Stop"

function Invoke-BlogApi {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [string]$Token = ""
    )

    $headers = @{}
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }

    if ($null -ne $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 8)
    }

    return Invoke-RestMethod -Method $Method -Uri $Url -Headers $headers
}

function Escape-Sql {
    param([string]$Value)
    if ($null -eq $Value) {
        return "NULL"
    }
    return "'" + $Value.Replace("\", "\\").Replace("'", "''") + "'"
}

function Invoke-MySqlQuery {
    param([string]$Sql)
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -LiteralPath $tempFile -Value $Sql -Encoding UTF8
        Get-Content -LiteralPath $tempFile | & $MysqlExe "--user=$DbUser" "--password=$DbPassword" "--host=$DbHost" "--port=$DbPort" "--database=$DbName" "--default-character-set=utf8mb4"
    } finally {
        Remove-Item -LiteralPath $tempFile -ErrorAction SilentlyContinue
    }
}

function Invoke-MySqlScalarList {
    param([string]$Sql)
    $output = & $MysqlExe "--user=$DbUser" "--password=$DbPassword" "--host=$DbHost" "--port=$DbPort" "--database=$DbName" "--default-character-set=utf8mb4" "--batch" "--skip-column-names" "--execute=$Sql"
    return @($output | Where-Object { $_ -and $_.Trim() })
}

Write-Host "Ensuring demo account exists..."
try {
    $null = Invoke-BlogApi -Method POST -Url "$BaseUrl/user/register" -Body @{
        username = $DemoUsername
        email = $DemoEmail
        password = $DemoPassword
    }
} catch {
    # Registration can fail when the user already exists. Login below is the source of truth.
}

$loginResult = Invoke-BlogApi -Method POST -Url "$BaseUrl/user/login" -Body @{
    account = $DemoUsername
    password = $DemoPassword
}
if ($loginResult.code -ne 0) {
    throw "Unable to login with demo account: $($loginResult.message)"
}

$demoUserId = [int]$loginResult.data.user_id
$demoToken = [string]$loginResult.data.token
Invoke-BlogApi -Method PUT -Url "$BaseUrl/user/preference" -Body @{ preference_tags = $PreferenceTags } -Token $demoToken | Out-Null

Write-Host "Cleaning previous demo data..."
$cleanupSql = @"
SET @demo_user_id := (SELECT id FROM user WHERE username = $(Escape-Sql $DemoUsername) LIMIT 1);
DELETE FROM recommendation WHERE user_id = @demo_user_id;
DELETE FROM user_behavior WHERE user_id = @demo_user_id;
DELETE FROM article_like WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id = @demo_user_id AND title LIKE 'Paper Demo - %') AS t);
DELETE FROM article_collect WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id = @demo_user_id AND title LIKE 'Paper Demo - %') AS t);
DELETE FROM comment WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id = @demo_user_id AND title LIKE 'Paper Demo - %') AS t);
DELETE FROM user_behavior WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id = @demo_user_id AND title LIKE 'Paper Demo - %') AS t);
DELETE FROM article WHERE author_id = @demo_user_id AND title LIKE 'Paper Demo - %';
UPDATE user SET preference_tags = $(Escape-Sql $PreferenceTags) WHERE id = @demo_user_id;
"@
Invoke-MySqlQuery -Sql $cleanupSql

Write-Host "Creating demo articles..."
$articleTemplates = @(
    @{ Title = "Paper Demo - Hybrid Recommendation Practice"; Category = "ai"; Tags = "ai,recommendation,tfidf"; Summary = "A practical article about hybrid recommendation and profile modeling."; Content = "# Hybrid Recommendation`n`nThis demo article explains hybrid recommendation, semantic matching, collaborative filtering, and ranking strategy." },
    @{ Title = "Paper Demo - Vue Dashboard Design"; Category = "frontend"; Tags = "vue,frontend,analytics"; Summary = "A practical article about Vue dashboard layouts and charts."; Content = "# Vue Dashboard`n`nThis demo article explains dashboard information design, card grouping, and chart arrangement." },
    @{ Title = "Paper Demo - Reading Behavior Analytics"; Category = "analytics"; Tags = "analytics,behavior,echarts"; Summary = "A practical article about reading duration, scroll depth, and event tracking."; Content = "# Reading Behavior Analytics`n`nThis demo article explains reading duration, scroll depth, and behavior event reporting." },
    @{ Title = "Paper Demo - User Portrait Modeling"; Category = "analytics"; Tags = "portrait,analytics,user"; Summary = "A practical article about portrait tags, activity windows, and behavior grouping."; Content = "# User Portrait`n`nThis demo article explains active hours, preferred categories, and user portrait indicators." },
    @{ Title = "Paper Demo - Collaborative Filtering Basics"; Category = "ai"; Tags = "collaborative,ai,recommendation"; Summary = "A practical article about collaborative filtering and nearest-neighbor scoring."; Content = "# Collaborative Filtering`n`nThis demo article explains overlap behavior, nearest neighbors, and weighted scoring." },
    @{ Title = "Paper Demo - Content Semantic Ranking"; Category = "ai"; Tags = "semantic,tfidf,recommendation"; Summary = "A practical article about text vectorization and semantic similarity ranking."; Content = "# Content Ranking`n`nThis demo article explains text cleaning, tokenization, and content similarity." },
    @{ Title = "Paper Demo - Responsive Blog Layout"; Category = "frontend"; Tags = "responsive,vue,layout"; Summary = "A practical article about adaptive blog layouts for desktop and mobile."; Content = "# Responsive Layout`n`nThis demo article explains layout adaptation, media queries, and card rearrangement." },
    @{ Title = "Paper Demo - Recommendation Evaluation"; Category = "analytics"; Tags = "evaluation,recommendation,ctr"; Summary = "A practical article about click-through rate, conversion, and recommendation evaluation."; Content = "# Recommendation Evaluation`n`nThis demo article explains CTR, conversion, source analysis, and effect comparison." }
)

$insertArticleRows = New-Object System.Collections.Generic.List[string]
for ($i = 0; $i -lt $articleTemplates.Count; $i++) {
    $daysAgo = 13 - $i
    $createTime = (Get-Date).ToUniversalTime().AddDays(-$daysAgo).AddHours(8 + ($i % 4)).AddMinutes(12 + ($i * 5))
    $template = $articleTemplates[$i]
    $html = "<h1>$($template.Title)</h1><p>$($template.Summary)</p>"
    $insertArticleRows.Add("(" +
        "$demoUserId," +
        "$(Escape-Sql $template.Title)," +
        "$(Escape-Sql $template.Content)," +
        "$(Escape-Sql $html)," +
        "$(Escape-Sql $template.Summary)," +
        "$(Escape-Sql $template.Category)," +
        "$(Escape-Sql $template.Tags)," +
        "'published'," +
        "0,0,0,0,0," +
        "$(Escape-Sql ($createTime.ToString('yyyy-MM-dd HH:mm:ss')))," +
        "$(Escape-Sql ($createTime.ToString('yyyy-MM-dd HH:mm:ss')))" +
    ")")
}
$insertArticleSql = "INSERT INTO article (author_id, title, content, html_content, summary, category, tags, status, view_count, like_count, collect_count, comment_count, is_deleted, create_time, update_time) VALUES " + ($insertArticleRows -join ",") + ";"
Invoke-MySqlQuery -Sql $insertArticleSql

$demoArticleIds = Invoke-MySqlScalarList -Sql "SELECT id FROM article WHERE author_id = $demoUserId AND title LIKE 'Paper Demo - %' ORDER BY create_time ASC;"
if ($demoArticleIds.Count -lt 6) {
    throw "Failed to create demo articles."
}

$readerIds = Invoke-MySqlScalarList -Sql "SELECT id FROM user WHERE id <> $demoUserId ORDER BY id LIMIT 10;"
$globalArticleIds = Invoke-MySqlScalarList -Sql "SELECT id FROM article WHERE is_deleted = 0 AND status = 'published' ORDER BY id LIMIT 30;"
$externalArticleIds = Invoke-MySqlScalarList -Sql "SELECT id FROM article WHERE is_deleted = 0 AND status = 'published' AND author_id <> $demoUserId ORDER BY id LIMIT 20;"
if ($externalArticleIds.Count -eq 0) {
    $externalArticleIds = $demoArticleIds
}

Write-Host "Generating behavior, interaction, and recommendation records..."
$behaviorRows = New-Object System.Collections.Generic.List[string]
$likeRows = New-Object System.Collections.Generic.List[string]
$collectRows = New-Object System.Collections.Generic.List[string]
$commentRows = New-Object System.Collections.Generic.List[string]
$recommendationRows = New-Object System.Collections.Generic.List[string]
$likeSeen = New-Object 'System.Collections.Generic.HashSet[string]'
$collectSeen = New-Object 'System.Collections.Generic.HashSet[string]'

for ($articleIndex = 0; $articleIndex -lt $demoArticleIds.Count; $articleIndex++) {
    $articleId = [int]$demoArticleIds[$articleIndex]
    for ($dayOffset = 0; $dayOffset -lt 14; $dayOffset++) {
        $readsToday = 2 + (($articleIndex + $dayOffset) % 4)
        for ($readIndex = 0; $readIndex -lt $readsToday; $readIndex++) {
            $readerId = [int]$readerIds[($articleIndex + $dayOffset + $readIndex) % $readerIds.Count]
            $readTime = (Get-Date).ToUniversalTime().AddDays(-$dayOffset).Date.AddHours(9 + (($articleIndex * 2 + $readIndex * 3) % 10)).AddMinutes(($readIndex * 11 + $articleIndex * 7) % 60)
            $duration = 70 + (($articleIndex * 31 + $dayOffset * 17 + $readIndex * 13) % 320)
            $depth = [math]::Round((0.32 + ((($articleIndex + $dayOffset + $readIndex) % 11) * 0.06)), 2)
            if ($depth -gt 0.98) { $depth = 0.98 }
            $behaviorRows.Add("($readerId,$articleId,'read',$duration,$depth,NULL,$(Escape-Sql ($readTime.ToString('yyyy-MM-dd HH:mm:ss'))))")

            if ((($articleIndex + $dayOffset + $readIndex) % 5) -eq 0) {
                $likeKey = "$readerId-$articleId"
                if ($likeSeen.Add($likeKey)) {
                    $likeRows.Add("($readerId,$articleId,$(Escape-Sql ($readTime.AddMinutes(5).ToString('yyyy-MM-dd HH:mm:ss'))))")
                }
            }
            if ((($articleIndex + $dayOffset + $readIndex) % 7) -eq 0) {
                $collectKey = "$readerId-$articleId"
                if ($collectSeen.Add($collectKey)) {
                    $collectRows.Add("($readerId,$articleId,$(Escape-Sql ($readTime.AddMinutes(8).ToString('yyyy-MM-dd HH:mm:ss'))))")
                }
            }
            if ((($articleIndex + $dayOffset + $readIndex) % 6) -eq 0) {
                $commentTime = $readTime.AddMinutes(12)
                $commentRows.Add("($articleId,$readerId,$(Escape-Sql ('Insightful point #' + ($articleIndex + $dayOffset + $readIndex + 1))),0,$(Escape-Sql ($commentTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
                $behaviorRows.Add("($readerId,$articleId,'comment',NULL,NULL,NULL,$(Escape-Sql ($commentTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
            }
        }
    }
}

for ($dayOffset = 0; $dayOffset -lt 14; $dayOffset++) {
    $dayBase = (Get-Date).ToUniversalTime().AddDays(-$dayOffset).Date
    $recommendTypes = @("hybrid", "content_semantic", "collaborative_filtering", "cold_start", "new_article_cold_start")
    for ($recIndex = 0; $recIndex -lt $recommendTypes.Count; $recIndex++) {
        $articleId = [int]$externalArticleIds[($dayOffset + $recIndex) % $externalArticleIds.Count]
        $recommendTime = $dayBase.AddHours(8 + $recIndex * 2).AddMinutes(($dayOffset * 7) % 45)
        $clicked = if ((($dayOffset + $recIndex) % 4) -ne 0) { 1 } else { 0 }
        $score = [math]::Round((0.48 + ($recIndex * 0.09) + (($dayOffset % 5) * 0.03)), 4)
        $recommendationRows.Add("($demoUserId,$articleId,$(Escape-Sql $recommendTypes[$recIndex]),$score,$clicked,$(Escape-Sql ($recommendTime.ToString('yyyy-MM-dd HH:mm:ss'))))")

        if ($clicked -eq 1) {
            $readDuration = 95 + (($dayOffset * 19 + $recIndex * 23) % 280)
            $scrollDepth = [math]::Round((0.42 + (($dayOffset + $recIndex) % 8) * 0.07), 2)
            if ($scrollDepth -gt 0.99) { $scrollDepth = 0.99 }
            $behaviorRows.Add("($demoUserId,$articleId,'read',$readDuration,$scrollDepth,NULL,$(Escape-Sql ($recommendTime.AddMinutes(6).ToString('yyyy-MM-dd HH:mm:ss'))))")
        }

        if ($clicked -eq 1 -and ((($dayOffset + $recIndex) % 3) -eq 0)) {
            $convertTime = $recommendTime.AddMinutes(18)
            $behaviorRows.Add("($demoUserId,$articleId,'comment',NULL,NULL,NULL,$(Escape-Sql ($convertTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
            $commentRows.Add("($articleId,$demoUserId,$(Escape-Sql ('Demo conversion comment ' + ($dayOffset + $recIndex + 1))),0,$(Escape-Sql ($convertTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
        } elseif ($clicked -eq 1 -and ((($dayOffset + $recIndex) % 4) -eq 0)) {
            $convertTime = $recommendTime.AddMinutes(20)
            $behaviorRows.Add("($demoUserId,$articleId,'collect',NULL,NULL,NULL,$(Escape-Sql ($convertTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
        }
    }
}

for ($dayOffset = 0; $dayOffset -lt 7; $dayOffset++) {
    $activityBase = (Get-Date).ToUniversalTime().AddDays(-$dayOffset).Date
    $searchKeyword = @("hybrid ranking", "vue charts", "reading analytics", "user portrait", "responsive layout", "content ranking", "ctr analysis")[$dayOffset]
    $behaviorRows.Add("($demoUserId,NULL,'search',NULL,NULL,$(Escape-Sql $searchKeyword),$(Escape-Sql ($activityBase.AddHours(9).ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,NULL,'page_view',NULL,NULL,$(Escape-Sql '/analysis/read-trend'),$(Escape-Sql ($activityBase.AddHours(9).AddMinutes(3).ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,NULL,'page_leave',NULL,NULL,$(Escape-Sql '/analysis/read-trend'),$(Escape-Sql ($activityBase.AddHours(9).AddMinutes(17).ToString('yyyy-MM-dd HH:mm:ss'))))")

    $portraitArticleId = [int]$globalArticleIds[$dayOffset % $globalArticleIds.Count]
    $likeBehaviorTime = $activityBase.AddHours(20).AddMinutes($dayOffset * 3)
    $collectBehaviorTime = $activityBase.AddHours(21).AddMinutes($dayOffset * 2)
    $behaviorRows.Add("($demoUserId,$portraitArticleId,'like',NULL,NULL,NULL,$(Escape-Sql ($likeBehaviorTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,$portraitArticleId,'collect',NULL,NULL,NULL,$(Escape-Sql ($collectBehaviorTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
}

$insertStatements = New-Object System.Collections.Generic.List[string]
if ($behaviorRows.Count -gt 0) {
    $insertStatements.Add("INSERT INTO user_behavior (user_id, article_id, behavior_type, read_duration, scroll_depth, keyword, create_time) VALUES " + ($behaviorRows -join ",") + ";")
}
if ($likeRows.Count -gt 0) {
    $insertStatements.Add("INSERT INTO article_like (user_id, article_id, create_time) VALUES " + ($likeRows -join ",") + ";")
}
if ($collectRows.Count -gt 0) {
    $insertStatements.Add("INSERT INTO article_collect (user_id, article_id, create_time) VALUES " + ($collectRows -join ",") + ";")
}
if ($commentRows.Count -gt 0) {
    $insertStatements.Add("INSERT INTO comment (article_id, user_id, content, parent_id, create_time) VALUES " + ($commentRows -join ",") + ";")
}
if ($recommendationRows.Count -gt 0) {
    $insertStatements.Add("INSERT INTO recommendation (user_id, article_id, recommend_type, recommend_score, is_clicked, create_time) VALUES " + ($recommendationRows -join ",") + ";")
}

$insertStatements.Add(@"
UPDATE article a
SET
    a.view_count = (SELECT COUNT(*) FROM user_behavior b WHERE b.article_id = a.id AND b.behavior_type = 'read'),
    a.like_count = (SELECT COUNT(*) FROM article_like l WHERE l.article_id = a.id),
    a.collect_count = (SELECT COUNT(*) FROM article_collect c WHERE c.article_id = a.id),
    a.comment_count = (SELECT COUNT(*) FROM comment m WHERE m.article_id = a.id),
    a.update_time = UTC_TIMESTAMP()
WHERE a.author_id = $demoUserId AND a.title LIKE 'Paper Demo - %';
"@)

Invoke-MySqlQuery -Sql ($insertStatements -join "`n")

Write-Host "Demo data seeded successfully."
Write-Host "Demo account:"
Write-Host "  Username: $DemoUsername"
Write-Host "  Password: $DemoPassword"
Write-Host "  User ID : $demoUserId"
