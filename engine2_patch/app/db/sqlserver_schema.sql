IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'market')
    EXEC(N'CREATE SCHEMA market');
GO
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'audit')
    EXEC(N'CREATE SCHEMA audit');
GO

IF OBJECT_ID(N'market.PriceCandles', N'U') IS NULL
BEGIN
    CREATE TABLE market.PriceCandles (
        PriceCandleId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_PriceCandles PRIMARY KEY,
        Symbol VARCHAR(32) NOT NULL,
        IntervalCode VARCHAR(16) NOT NULL,
        TimestampUtc DATETIME2(3) NOT NULL,
        [Open] FLOAT NOT NULL,
        High FLOAT NOT NULL,
        Low FLOAT NOT NULL,
        [Close] FLOAT NOT NULL,
        AdjClose FLOAT NULL,
        Volume FLOAT NULL,
        SourceName VARCHAR(32) NOT NULL CONSTRAINT DF_PriceCandles_Source DEFAULT ('yahoo_finance'),
        CollectedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_PriceCandles_Collected DEFAULT (SYSUTCDATETIME()),
        CONSTRAINT UQ_PriceCandles UNIQUE (Symbol, IntervalCode, TimestampUtc),
        CONSTRAINT CK_PriceCandles_OHLC CHECK (
            [Open] > 0 AND High > 0 AND Low > 0 AND [Close] > 0
            AND High >= [Open] AND High >= [Close] AND High >= Low
            AND Low <= [Open] AND Low <= [Close]
        )
    );
    CREATE INDEX IX_PriceCandles_Lookup
        ON market.PriceCandles(Symbol, IntervalCode, TimestampUtc)
        INCLUDE ([Open], High, Low, [Close], Volume);
END;
GO

IF OBJECT_ID(N'audit.CollectionRuns', N'U') IS NULL
BEGIN
    CREATE TABLE audit.CollectionRuns (
        CollectionRunId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_CollectionRuns PRIMARY KEY,
        Symbol VARCHAR(32) NOT NULL,
        IntervalCode VARCHAR(16) NOT NULL,
        PeriodCode VARCHAR(16) NOT NULL,
        StartedAtUtc DATETIME2(3) NOT NULL,
        CompletedAtUtc DATETIME2(3) NULL,
        Status VARCHAR(16) NOT NULL,
        RowsReceived INT NOT NULL CONSTRAINT DF_CollectionRuns_Received DEFAULT (0),
        RowsWritten INT NOT NULL CONSTRAINT DF_CollectionRuns_Written DEFAULT (0),
        DuplicateRows INT NOT NULL CONSTRAINT DF_CollectionRuns_Duplicates DEFAULT (0),
        InvalidRows INT NOT NULL CONSTRAINT DF_CollectionRuns_Invalid DEFAULT (0),
        EarliestTimestampUtc DATETIME2(3) NULL,
        LatestTimestampUtc DATETIME2(3) NULL,
        ErrorMessage NVARCHAR(MAX) NULL
    );
END;
GO

IF OBJECT_ID('market.MarketAnalyses', 'U') IS NULL
BEGIN
    CREATE TABLE market.MarketAnalyses
    (
        AnalysisId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_MarketAnalyses PRIMARY KEY,
        Symbol VARCHAR(32) NOT NULL,
        IntervalCode VARCHAR(16) NOT NULL,
        CandleTimestampUtc DATETIME2(6) NOT NULL,
        AnalyzedAtUtc DATETIME2(6) NOT NULL CONSTRAINT DF_MarketAnalyses_AnalyzedAt DEFAULT SYSUTCDATETIME(),
        LastPrice FLOAT NOT NULL,
        Ema20 FLOAT NOT NULL,
        Ema50 FLOAT NOT NULL,
        Ema200 FLOAT NULL,
        Rsi14 FLOAT NOT NULL,
        Atr14 FLOAT NOT NULL,
        AtrPercent FLOAT NOT NULL,
        Trend VARCHAR(32) NOT NULL,
        MarketRegime VARCHAR(32) NOT NULL,
        Bias VARCHAR(16) NOT NULL,
        Confidence FLOAT NOT NULL CONSTRAINT CK_MarketAnalyses_Confidence CHECK (Confidence BETWEEN 0 AND 1),
        SupportLevelsJson NVARCHAR(MAX) NOT NULL,
        ResistanceLevelsJson NVARCHAR(MAX) NOT NULL,
        InvalidationLevel FLOAT NULL,
        DataQuality VARCHAR(128) NOT NULL,
        ReasonsJson NVARCHAR(MAX) NOT NULL
    );
    CREATE INDEX IX_MarketAnalyses_Lookup
        ON market.MarketAnalyses(Symbol, IntervalCode, AnalyzedAtUtc DESC);
END;
GO

IF OBJECT_ID('news.NewsArticles', 'U') IS NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'news') EXEC(N'CREATE SCHEMA news');
    CREATE TABLE news.NewsArticles
    (
        NewsArticleId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_NewsArticles PRIMARY KEY,
        ArticleHash CHAR(64) NOT NULL CONSTRAINT UQ_NewsArticles_Hash UNIQUE,
        Title NVARCHAR(MAX) NOT NULL,
        Url NVARCHAR(MAX) NOT NULL,
        SourceName NVARCHAR(255) NOT NULL,
        SourceType VARCHAR(64) NOT NULL,
        PublishedAtUtc DATETIME2(6) NOT NULL,
        Summary NVARCHAR(MAX) NOT NULL,
        LanguageName NVARCHAR(64) NOT NULL,
        Reliability FLOAT NOT NULL,
        CollectedAtUtc DATETIME2(6) NOT NULL CONSTRAINT DF_NewsArticles_Collected DEFAULT SYSUTCDATETIME()
    );
    CREATE INDEX IX_NewsArticles_Published ON news.NewsArticles(PublishedAtUtc DESC);
END;
GO

IF OBJECT_ID('news.NewsAnalyses', 'U') IS NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = N'news') EXEC(N'CREATE SCHEMA news');
    CREATE TABLE news.NewsAnalyses
    (
        NewsAnalysisId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_NewsAnalyses PRIMARY KEY,
        Symbol VARCHAR(32) NOT NULL,
        AnalyzedAtUtc DATETIME2(6) NOT NULL CONSTRAINT DF_NewsAnalyses_Analyzed DEFAULT SYSUTCDATETIME(),
        ArticleCount INT NOT NULL,
        RelevantArticleCount INT NOT NULL,
        SourceCount INT NOT NULL,
        Bias VARCHAR(16) NOT NULL,
        Score FLOAT NOT NULL,
        Confidence FLOAT NOT NULL CONSTRAINT CK_NewsAnalyses_Confidence CHECK (Confidence BETWEEN 0 AND 1),
        HighImpactCount INT NOT NULL,
        Summary NVARCHAR(MAX) NOT NULL,
        DriversJson NVARCHAR(MAX) NOT NULL,
        WarningsJson NVARCHAR(MAX) NOT NULL,
        ModelName NVARCHAR(128) NOT NULL,
        DataQuality VARCHAR(32) NOT NULL
    );
    CREATE INDEX IX_NewsAnalyses_Lookup ON news.NewsAnalyses(Symbol, AnalyzedAtUtc DESC);
END;
GO
