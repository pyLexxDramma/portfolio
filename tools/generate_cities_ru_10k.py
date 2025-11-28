import argparse
import csv
import json
from collections import defaultdict
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Сгенерировать JSON со списком городов России по регионам "
            "из CSV Росстата (или похожего формата)."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Путь к CSV‑файлу Росстата с городами и населением",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="src/webapp/static/cities_ru_10k.json",
        help="Путь для сохранения JSON (по умолчанию src/webapp/static/cities_ru_10k.json)",
    )
    parser.add_argument(
        "--min-population",
        type=int,
        default=10_000,
        help="Минимальное население города (по умолчанию 10 000)",
    )
    # Названия колонок. Для CSV Росстата 2021/2022 подойдут значения по умолчанию ниже.
    parser.add_argument(
        "--region-col",
        default="region",
        help="Имя колонки с регионом / субъектом РФ в CSV",
    )
    parser.add_argument(
        "--city-col",
        default="settlement_name",
        help="Имя колонки с названием города в CSV",
    )
    parser.add_argument(
        "--population-col",
        default="pop_total",
        help="Имя колонки с численностью населения в CSV",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Кодировка входного CSV (по умолчанию utf-8; для некоторых файлов Росстата может быть cp1251)",
    )
    parser.add_argument(
        "--delimiter",
        default=";",
        help="Разделитель в CSV (по умолчанию ';' как в файлах Росстата)",
    )
    return parser.parse_args()


def load_cities(
    path: str,
    encoding: str,
    delimiter: str,
    region_col: str,
    city_col: str,
    population_col: str,
    min_population: int,
) -> Dict[str, List[str]]:
    regions: Dict[str, List[str]] = defaultdict(list)

    with open(path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        missing = [c for c in (region_col, city_col, population_col) if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"В CSV не найдены колонки: {', '.join(missing)}. "
                f"Доступные колонки: {', '.join(reader.fieldnames or [])}"
            )

        for row in reader:
            try:
                region = (row.get(region_col) or "").strip()
                city = (row.get(city_col) or "").strip()
                pop_raw = (row.get(population_col) or "").replace(" ", "").replace("\u00a0", "")
                if not region or not city or not pop_raw:
                    continue
                population = int(pop_raw)
            except (ValueError, TypeError):
                continue

            if population < min_population:
                continue

            if city not in regions[region]:
                regions[region].append(city)

    # Сортируем города внутри региона и регионы по алфавиту
    for reg in regions:
        regions[reg].sort()

    return dict(sorted(regions.items(), key=lambda kv: kv[0]))


def main() -> None:
    args = parse_args()

    regions = load_cities(
        path=args.input,
        encoding=args.encoding,
        delimiter=args.delimiter,
        region_col=args.region_col,
        city_col=args.city_col,
        population_col=args.population_col,
        min_population=args.min_population,
    )

    data = [
        {"region": region, "cities": cities}
        for region, cities in regions.items()
        if cities
    ]

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(
        f"Готово. Регионов: {len(data)}, всего городов: "
        f"{sum(len(r['cities']) for r in data)}. "
        f"JSON записан в {args.output}"
    )


if __name__ == "__main__":
    main()


