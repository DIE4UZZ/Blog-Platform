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
    [string]$PreferenceTags = "ai,recommendation,analytics,frontend",
    [int]$SeedDays = 30
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

function Invoke-MySqlScalar {
    param([string]$Sql)
    $values = Invoke-MySqlScalarList -Sql $Sql
    if ($values.Count -eq 0) {
        return $null
    }
    return $values[0]
}

function Ensure-Account {
    param(
        [string]$Username,
        [string]$Email,
        [string]$Password,
        [string]$Preference = ""
    )

    try {
        $null = Invoke-BlogApi -Method POST -Url "$BaseUrl/user/register" -Body @{
            username = $Username
            email = $Email
            password = $Password
        }
    } catch {
        # Re-registration is expected on repeated runs.
    }

    $loginResult = Invoke-BlogApi -Method POST -Url "$BaseUrl/user/login" -Body @{
        account = $Username
        password = $Password
    }
    if ($loginResult.code -ne 0) {
        throw "Unable to login with account $Username: $($loginResult.message)"
    }

    if ($Preference) {
        Invoke-BlogApi -Method PUT -Url "$BaseUrl/user/preference" -Body @{
            preference_tags = $Preference
        } -Token ([string]$loginResult.data.token) | Out-Null
    }

    return $loginResult
}

Write-Host "Ensuring demo account exists..."
$demoLogin = Ensure-Account -Username $DemoUsername -Email $DemoEmail -Password $DemoPassword -Preference $PreferenceTags
$demoUserId = [int]$demoLogin.data.user_id
$demoToken = [string]$demoLogin.data.token

$socialUserSpecs = @(
    @{ Username = "paper_demo_author_ai"; Email = "paper_demo_author_ai@example.com"; PreferenceTags = "ai,recommendation,semantic" },
    @{ Username = "paper_demo_author_frontend"; Email = "paper_demo_author_frontend@example.com"; PreferenceTags = "frontend,vue,responsive" },
    @{ Username = "paper_demo_author_data"; Email = "paper_demo_author_data@example.com"; PreferenceTags = "analytics,visualization,behavior" },
    @{ Username = "paper_demo_reader_a"; Email = "paper_demo_reader_a@example.com"; PreferenceTags = "ai,analytics,blog" },
    @{ Username = "paper_demo_reader_b"; Email = "paper_demo_reader_b@example.com"; PreferenceTags = "frontend,design,content" }
)

Write-Host "Ensuring supporting social accounts exist..."
foreach ($spec in $socialUserSpecs) {
    $null = Ensure-Account -Username $spec.Username -Email $spec.Email -Password $DemoPassword -Preference $spec.PreferenceTags
}

$userIdMap = @{}
$userIdMap[$DemoUsername] = $demoUserId
foreach ($spec in $socialUserSpecs) {
    $userId = Invoke-MySqlScalar -Sql "SELECT id FROM user WHERE username = $(Escape-Sql $($spec.Username)) LIMIT 1;"
    if ($null -eq $userId) {
        throw "Unable to resolve id for $($spec.Username)"
    }
    $userIdMap[$spec.Username] = [int]$userId
}

$authorAiId = [int]$userIdMap["paper_demo_author_ai"]
$authorFrontendId = [int]$userIdMap["paper_demo_author_frontend"]
$authorDataId = [int]$userIdMap["paper_demo_author_data"]
$readerAId = [int]$userIdMap["paper_demo_reader_a"]
$readerBId = [int]$userIdMap["paper_demo_reader_b"]
$allDemoUserIds = @(
    $demoUserId,
    $authorAiId,
    $authorFrontendId,
    $authorDataId,
    $readerAId,
    $readerBId
)
$allDemoUserIdsSql = ($allDemoUserIds | Sort-Object -Unique) -join ","

Write-Host "Cleaning previous demo data..."
$cleanupSql = @"
DELETE FROM recommendation WHERE user_id IN ($allDemoUserIdsSql);
DELETE FROM user_notification WHERE user_id IN ($allDemoUserIdsSql) OR actor_user_id IN ($allDemoUserIdsSql);
DELETE FROM user_follow WHERE follower_id IN ($allDemoUserIdsSql) OR following_id IN ($allDemoUserIdsSql);
DELETE FROM article_like WHERE user_id IN ($allDemoUserIdsSql);
DELETE FROM article_collect WHERE user_id IN ($allDemoUserIdsSql);
DELETE FROM comment WHERE user_id IN ($allDemoUserIdsSql);
DELETE FROM user_behavior WHERE user_id IN ($allDemoUserIdsSql);
DELETE FROM article_like WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id IN ($allDemoUserIdsSql) AND (title LIKE 'Paper Demo - %' OR title LIKE 'Paper Social - %')) AS t);
DELETE FROM article_collect WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id IN ($allDemoUserIdsSql) AND (title LIKE 'Paper Demo - %' OR title LIKE 'Paper Social - %')) AS t);
DELETE FROM comment WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id IN ($allDemoUserIdsSql) AND (title LIKE 'Paper Demo - %' OR title LIKE 'Paper Social - %')) AS t);
DELETE FROM user_behavior WHERE article_id IN (SELECT id FROM (SELECT id FROM article WHERE author_id IN ($allDemoUserIdsSql) AND (title LIKE 'Paper Demo - %' OR title LIKE 'Paper Social - %')) AS t);
DELETE FROM article WHERE author_id IN ($allDemoUserIdsSql) AND (title LIKE 'Paper Demo - %' OR title LIKE 'Paper Social - %');
UPDATE user SET preference_tags = $(Escape-Sql $PreferenceTags) WHERE id = $demoUserId;
"@
Invoke-MySqlQuery -Sql $cleanupSql

Write-Host "Creating demo articles..."
$demoArticleTemplates = @(
    @{ Title = "Paper Demo - Hybrid Recommendation Practice"; Category = "ai"; Tags = "ai,recommendation,tfidf"; Summary = "A practical article about hybrid recommendation and profile modeling."; Content = "# Hybrid Recommendation`n`nThis demo article explains hybrid recommendation, semantic matching, collaborative filtering, and ranking strategy." },
    @{ Title = "Paper Demo - Vue Dashboard Design"; Category = "frontend"; Tags = "vue,frontend,analytics"; Summary = "A practical article about Vue dashboard layouts and charts."; Content = "# Vue Dashboard`n`nThis demo article explains dashboard information design, card grouping, and chart arrangement." },
    @{ Title = "Paper Demo - Reading Behavior Analytics"; Category = "analytics"; Tags = "analytics,behavior,echarts"; Summary = "A practical article about reading duration, scroll depth, and event tracking."; Content = "# Reading Behavior Analytics`n`nThis demo article explains reading duration, scroll depth, and behavior event reporting." },
    @{ Title = "Paper Demo - User Portrait Modeling"; Category = "analytics"; Tags = "portrait,analytics,user"; Summary = "A practical article about portrait tags, activity windows, and behavior grouping."; Content = "# User Portrait`n`nThis demo article explains active hours, preferred categories, and user portrait indicators." },
    @{ Title = "Paper Demo - Collaborative Filtering Basics"; Category = "ai"; Tags = "collaborative,ai,recommendation"; Summary = "A practical article about collaborative filtering and nearest-neighbor scoring."; Content = "# Collaborative Filtering`n`nThis demo article explains overlap behavior, nearest neighbors, and weighted scoring." },
    @{ Title = "Paper Demo - Content Semantic Ranking"; Category = "ai"; Tags = "semantic,tfidf,recommendation"; Summary = "A practical article about text vectorization and semantic similarity ranking."; Content = "# Content Ranking`n`nThis demo article explains text cleaning, tokenization, and content similarity." },
    @{ Title = "Paper Demo - Responsive Blog Layout"; Category = "frontend"; Tags = "responsive,vue,layout"; Summary = "A practical article about adaptive blog layouts for desktop and mobile."; Content = "# Responsive Layout`n`nThis demo article explains layout adaptation, media queries, and card rearrangement." },
    @{ Title = "Paper Demo - Recommendation Evaluation"; Category = "analytics"; Tags = "evaluation,recommendation,ctr"; Summary = "A practical article about click-through rate, conversion, and recommendation evaluation."; Content = "# Recommendation Evaluation`n`nThis demo article explains CTR, conversion, source analysis, and effect comparison." }
)

$socialArticleTemplates = @(
    @{ AuthorId = $authorAiId; Title = "Paper Social - Semantic Ranking Diary"; Category = "ai"; Tags = "semantic,recommendation,ranking"; Summary = "Recent notes on semantic ranking, candidate recall, and recommendation ordering."; Content = "# Semantic Ranking Diary`n`nA followed author shares recent progress on semantic ranking and recommendation ordering."; DayOffset = 0; Hour = 9; Minute = 10 },
    @{ AuthorId = $authorFrontendId; Title = "Paper Social - Mobile Card Layout Notes"; Category = "frontend"; Tags = "responsive,layout,vue"; Summary = "A design note on adaptive card layout, spacing, and mobile reading experience."; Content = "# Mobile Card Layout Notes`n`nThis article focuses on responsive layout details for the blog platform."; DayOffset = 1; Hour = 11; Minute = 25 },
    @{ AuthorId = $authorDataId; Title = "Paper Social - Reader Activity Heatmap"; Category = "analytics"; Tags = "analytics,heatmap,behavior"; Summary = "A practical walkthrough for active-hour heatmaps and user behavior visualization."; Content = "# Reader Activity Heatmap`n`nThis article discusses reader activity windows and heatmap indicators."; DayOffset = 2; Hour = 14; Minute = 40 },
    @{ AuthorId = $authorAiId; Title = "Paper Social - Cold Start Tradeoffs"; Category = "ai"; Tags = "cold-start,recommendation,profile"; Summary = "Thoughts about balancing hot content, profile tags, and new-article exposure."; Content = "# Cold Start Tradeoffs`n`nThis article discusses cold-start strategies for a lightweight blog recommender."; DayOffset = 4; Hour = 16; Minute = 5 },
    @{ AuthorId = $authorFrontendId; Title = "Paper Social - Dashboard Readability Review"; Category = "frontend"; Tags = "dashboard,ux,charts"; Summary = "A review of dashboard readability, color hierarchy, and chart comparison."; Content = "# Dashboard Readability Review`n`nThis article focuses on information hierarchy in analytics dashboards."; DayOffset = 5; Hour = 10; Minute = 35 },
    @{ AuthorId = $authorDataId; Title = "Paper Social - Notification Interaction Metrics"; Category = "analytics"; Tags = "notification,ctr,analytics"; Summary = "A short note about measuring notification exposure, click-through, and conversion."; Content = "# Notification Interaction Metrics`n`nThis article explains how notification metrics can support content operations."; DayOffset = 6; Hour = 18; Minute = 20 }
)

$insertArticleRows = New-Object System.Collections.Generic.List[string]
for ($i = 0; $i -lt $demoArticleTemplates.Count; $i++) {
    $daysAgo = [math]::Max(($SeedDays - 1) - ($demoArticleTemplates.Count - 1) + $i, 0)
    $createTime = (Get-Date).ToUniversalTime().AddDays(-$daysAgo).AddHours(8 + ($i % 4)).AddMinutes(12 + ($i * 5))
    $template = $demoArticleTemplates[$i]
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

foreach ($template in $socialArticleTemplates) {
    $createTime = (Get-Date).ToUniversalTime().AddDays(-[int]$template.DayOffset).Date.AddHours([int]$template.Hour).AddMinutes([int]$template.Minute)
    $html = "<h1>$($template.Title)</h1><p>$($template.Summary)</p>"
    $insertArticleRows.Add("(" +
        "$($template.AuthorId)," +
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

$socialArticleIdMap = @{}
foreach ($template in $socialArticleTemplates) {
    $articleId = Invoke-MySqlScalar -Sql "SELECT id FROM article WHERE author_id = $($template.AuthorId) AND title = $(Escape-Sql $($template.Title)) ORDER BY id DESC LIMIT 1;"
    if ($null -eq $articleId) {
        throw "Failed to resolve article id for $($template.Title)"
    }
    $socialArticleIdMap[$template.Title] = [int]$articleId
}

$readerIds = Invoke-MySqlScalarList -Sql "SELECT id FROM user WHERE id <> $demoUserId ORDER BY id LIMIT 12;"
if ($readerIds.Count -eq 0) {
    throw "At least one additional user is required for seeding."
}

$globalArticleIds = Invoke-MySqlScalarList -Sql "SELECT id FROM article WHERE is_deleted = 0 AND status = 'published' ORDER BY id LIMIT 30;"
$externalArticleIds = Invoke-MySqlScalarList -Sql "SELECT id FROM article WHERE is_deleted = 0 AND status = 'published' AND author_id <> $demoUserId ORDER BY id LIMIT 30;"
if ($externalArticleIds.Count -eq 0) {
    $externalArticleIds = $demoArticleIds
}

Write-Host "Generating analytics, follow, feed, and notification data..."
$behaviorRows = New-Object System.Collections.Generic.List[string]
$likeRows = New-Object System.Collections.Generic.List[string]
$collectRows = New-Object System.Collections.Generic.List[string]
$commentRows = New-Object System.Collections.Generic.List[string]
$recommendationRows = New-Object System.Collections.Generic.List[string]
$followRows = New-Object System.Collections.Generic.List[string]
$notificationRows = New-Object System.Collections.Generic.List[string]
$likeSeen = New-Object 'System.Collections.Generic.HashSet[string]'
$collectSeen = New-Object 'System.Collections.Generic.HashSet[string]'

for ($articleIndex = 0; $articleIndex -lt $demoArticleIds.Count; $articleIndex++) {
    $articleId = [int]$demoArticleIds[$articleIndex]
    for ($dayOffset = 0; $dayOffset -lt $SeedDays; $dayOffset++) {
        $readsToday = 2 + (($articleIndex + $dayOffset) % 5)
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

for ($dayOffset = 0; $dayOffset -lt $SeedDays; $dayOffset++) {
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

for ($dayOffset = 0; $dayOffset -lt [math]::Min($SeedDays, 21); $dayOffset++) {
    $activityBase = (Get-Date).ToUniversalTime().AddDays(-$dayOffset).Date
    $keywords = @(
        "hybrid ranking",
        "vue charts",
        "reading analytics",
        "user portrait",
        "responsive layout",
        "content ranking",
        "ctr analysis",
        "tfidf recommend",
        "blog behavior",
        "dashboard design",
        "semantic recall",
        "collaborative score",
        "author analytics",
        "cold start",
        "engagement rate",
        "read duration",
        "scroll depth",
        "article similarity",
        "heatmap active hour",
        "category hotness",
        "conversion trend"
    )
    $searchKeyword = $keywords[$dayOffset % $keywords.Count]
    $behaviorRows.Add("($demoUserId,NULL,'search',NULL,NULL,$(Escape-Sql $searchKeyword),$(Escape-Sql ($activityBase.AddHours(9).ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,NULL,'page_view',NULL,NULL,$(Escape-Sql '/analysis/read-trend'),$(Escape-Sql ($activityBase.AddHours(9).AddMinutes(3).ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,NULL,'page_leave',NULL,NULL,$(Escape-Sql '/analysis/read-trend'),$(Escape-Sql ($activityBase.AddHours(9).AddMinutes(17).ToString('yyyy-MM-dd HH:mm:ss'))))")

    $portraitArticleId = [int]$globalArticleIds[$dayOffset % $globalArticleIds.Count]
    $likeBehaviorTime = $activityBase.AddHours(20).AddMinutes($dayOffset * 3)
    $collectBehaviorTime = $activityBase.AddHours(21).AddMinutes($dayOffset * 2)
    $behaviorRows.Add("($demoUserId,$portraitArticleId,'like',NULL,NULL,NULL,$(Escape-Sql ($likeBehaviorTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
    $behaviorRows.Add("($demoUserId,$portraitArticleId,'collect',NULL,NULL,NULL,$(Escape-Sql ($collectBehaviorTime.ToString('yyyy-MM-dd HH:mm:ss'))))")
}
