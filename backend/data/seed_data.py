"""Generate and seed the SQLite database with realistic e-commerce data."""

import sqlite3
import random
import datetime
from pathlib import Path


CATEGORIES = {
    "电子产品": ["MacBook Pro 14", "iPhone 16 Pro", "iPad Air", "AirPods Pro", "Apple Watch Ultra",
                "Samsung Galaxy S25", "Dell XPS 16", "Sony WH-1000XM6", "罗技 MX Master 3S", "机械键盘"],
    "服装": ["Canada Goose 羽绒服", "始祖鸟 Beta Jacket", "Lululemon 瑜伽裤", "Nike Air Max",
            "北面冲锋衣", "优衣库羽绒服", "Zara 西装外套", "Adidas Ultraboost", "Patagonia 抓绒", "Ralph Lauren Polo"],
    "家居": ["戴森 V15 吸尘器", "Muji 香薰机", "Vitamix 破壁机", "Sonos Era 300", "Herman Miller 座椅",
            "飞利浦 咖啡机", "小米空气净化器", "松下吹风机", "摩卡壶", "智能台灯"],
    "食品": ["茅台酒", "五粮液", "有机橄榄油礼盒", "日本和牛套装", "云南普洱生茶",
            "松茸干货", "法国红酒套装", "精品咖啡豆", "挪威三文鱼", "意大利黑醋"],
    "运动": ["Trek 公路车", "划船机", "Peloton 单车", "瑜伽垫套装", "Wilson 网球拍",
            "Garmin 运动手表", "哑铃套装", "筋膜枪", "滑雪护目镜", "跑步腰带"],
}
REGIONS = ["华北", "华东", "华南", "华中", "西南", "西北", "东北"]
CITIES = {
    "华北": ["北京", "天津", "石家庄"],
    "华东": ["上海", "杭州", "南京", "苏州"],
    "华南": ["广州", "深圳", "东莞"],
    "华中": ["武汉", "长沙", "郑州"],
    "西南": ["成都", "重庆", "昆明"],
    "西北": ["西安", "兰州", "乌鲁木齐"],
    "东北": ["沈阳", "大连", "哈尔滨"],
}
SEGMENTS = ["企业客户", "个人消费", "小企业"]
CUSTOMER_NAMES = [
    "阿里巴巴", "腾讯科技", "字节跳动", "华为技术", "美团点评",
    "京东集团", "小米科技", "比亚迪", "宁德时代", "中兴通讯",
    "网易集团", "徐汇区李浩", "朝阳区王芳", "南山区张伟", "武侯区刘洋",
    "西湖区陈静", "天河区黄鑫", "鼓楼区赵磊", "张江科技园", "中关村创业谷",
]

# Price ranges by category
PRICE_RANGES = {
    "电子产品": (300, 25000),
    "服装": (299, 12000),
    "家居": (100, 5000),
    "食品": (88, 5000),
    "运动": (200, 30000),
}


def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name TEXT NOT NULL,
            segment TEXT NOT NULL,
            city TEXT NOT NULL,
            region TEXT NOT NULL,
            registered_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            order_date TEXT NOT NULL,
            region TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
        CREATE INDEX IF NOT EXISTS idx_orders_region ON orders(region);
        CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id);
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
    """)


def seed_database(db_path: str, num_orders: int = 500):
    """Generate realistic e-commerce data and populate the database."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    create_tables(conn)

    # Check if already seeded
    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    if count > 0:
        conn.close()
        return False  # Already seeded

    random.seed(42)

    # ---- Products ----
    products = []
    pid = 1
    for category, items in CATEGORIES.items():
        min_p, max_p = PRICE_RANGES[category]
        for name in items:
            price = round(random.uniform(min_p, max_p), 2)
            price = max(price, 1.0)
            products.append((pid, name, category, price))
            pid += 1
    conn.executemany(
        "INSERT INTO products (product_id, product_name, category, price) VALUES (?, ?, ?, ?)",
        products
    )

    # ---- Customers ----
    customers = []
    for i, name in enumerate(CUSTOMER_NAMES, 1):
        segment = SEGMENTS[i % 3]
        region = random.choice(REGIONS)
        city = random.choice(CITIES[region])
        reg_date = _random_date("2022-01-01", "2024-06-30")
        customers.append((i, name, segment, city, region, reg_date))
    conn.executemany(
        "INSERT INTO customers (customer_id, customer_name, segment, city, region, registered_at) VALUES (?, ?, ?, ?, ?, ?)",
        customers
    )

    # ---- Orders ----
    orders = []
    methods = ["微信支付", "支付宝", "银行转账", "信用卡", "企业对公"]
    statuses = ["completed", "completed", "completed", "completed", "refunded", "processing"]
    for oid in range(1, num_orders + 1):
        cid = random.randint(1, len(CUSTOMER_NAMES))
        pid = random.randint(1, len(products))
        qty = random.choices([1, 1, 1, 2, 2, 3, 5, 10], weights=[30, 20, 15, 10, 10, 8, 5, 2])[0]
        unit_price = products[pid - 1][3]
        total = round(unit_price * qty, 2)
        # Add some randomness: discount for larger orders
        if qty >= 5:
            total = round(total * 0.92, 2)  # 8% bulk discount
        order_date = _random_date("2024-01-01", "2025-12-31")
        region = random.choice(REGIONS)
        method = random.choice(methods)
        status = random.choice(statuses)

        orders.append((oid, cid, pid, qty, unit_price, total, order_date, region, method, status))
    conn.executemany(
        "INSERT INTO orders (order_id, customer_id, product_id, quantity, unit_price, total_amount, order_date, region, payment_method, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        orders
    )

    conn.commit()
    conn.close()
    return True


def _random_date(start: str, end: str) -> str:
    s = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    delta = (e - s).days
    d = s + datetime.timedelta(days=random.randint(0, delta))
    return d.isoformat()
