from freqtrade.configuration import Configuration
try:
    # Новый путь импорта в свежих версиях
    from freqtrade.resolvers import StrategyResolver
except Exception:
    # Фоллбэк на старые разметки пакетов
    from freqtrade.resolvers.strategy_resolver import StrategyResolver

def main():
    # Загружаем конфиг для бэктеста
    config = Configuration.from_files(["config_backtest.json"])
    # Подстраховка: явно задаём имя стратегии и путь к папке со стратегиями
    config["strategy"] = "NewsHeliusBitqueryML"
    config.setdefault("strategy_path", "strategies/")

    strategy = StrategyResolver.load_strategy(config)
    print("✅ Стратегия загружена:", strategy.__class__.__name__)

if __name__ == "__main__":
    main()