#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MoshimoNavi用：厚生労働省オープンデータから facilities.csv を自動生成するスクリプト。

使い方:
  python make_facilities_csv.py --mode core
  python make_facilities_csv.py --mode all
  python make_facilities_csv.py --mode core --pref 埼玉県

出力:
  facilities.csv

注意:
  全国全件をGitHub Pagesで読み込むとスマホ表示が重くなる可能性があります。
  最初は --pref 埼玉県 のように都道府県を絞る、または core のみにしてください。
"""
import argparse, csv, io, os, sys, zipfile, urllib.request, tempfile, re
from pathlib import Path

SOURCES = [
    # category, dataset_name, facility_type, data_date, url, recommended
    ('医療','病院（施設票）','病院','2025-12-01','https://www.mhlw.go.jp/content/11121000/01-1_hospital_facility_info_20251201.zip',True),
    ('医療','診療所（施設票）','診療所','2025-12-01','https://www.mhlw.go.jp/content/11121000/02-1_clinic_facility_info_20251201.zip',False),
    ('医療','薬局','薬局','2025-12-01','https://www.mhlw.go.jp/content/11121000/05_pharmacy_20251201.zip',False),
    ('介護','110_訪問介護','訪問介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_110.csv',False),
    ('介護','120_訪問入浴介護','訪問入浴介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_120.csv',False),
    ('介護','130_訪問看護','訪問看護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_130.csv',True),
    ('介護','140_訪問リハビリテーション','訪問リハビリ','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_140.csv',True),
    ('介護','150_通所介護','デイサービス','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_150.csv',True),
    ('介護','155_通所介護（療養通所介護）','療養通所介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_155.csv',True),
    ('介護','160_通所リハビリテーション','通所リハビリ','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_160.csv',True),
    ('介護','170_福祉用具貸与','福祉用具貸与','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_170.csv',False),
    ('介護','210_短期入所生活介護','ショートステイ','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_210.csv',True),
    ('介護','220_短期入所療養介護（介護老人保健施設）','短期入所療養介護_老健','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_220.csv',True),
    ('介護','230_短期入所療養介護（療養病床を有する病院等）','短期入所療養介護_病院等','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_230.csv',True),
    ('介護','551_短期入所療養介護（介護医療院）','短期入所療養介護_介護医療院','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_551.csv',True),
    ('介護','320_認知症対応型共同生活介護','グループホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_320.csv',True),
    ('介護','331_特定施設入居者生活介護（有料老人ホーム）','介護付き有料老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_331.csv',True),
    ('介護','332_特定施設入居者生活介護（軽費老人ホーム）','軽費老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_332.csv',True),
    ('介護','334_特定施設入居者生活介護（サービス付き高齢者向け住宅）','サービス付き高齢者向け住宅','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_334.csv',True),
    ('介護','335_特定施設入居者生活介護（有料老人ホーム・外部サービス利用型）','有料老人ホーム_外部サービス利用型','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_335.csv',True),
    ('介護','336_特定施設入居者生活介護（軽費老人ホーム・外部サービス利用型）','軽費老人ホーム_外部サービス利用型','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_336.csv',True),
    ('介護','337_特定施設入居者生活介護（サービス付き高齢者向け住宅・外部サービス利用型）','サ高住_外部サービス利用型','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_337.csv',True),
    ('介護','361_地域密着型特定施設入居者生活介護（有料老人ホーム）','地域密着型有料老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_361.csv',True),
    ('介護','362_地域密着型特定施設入居者生活介護（軽費老人ホーム）','地域密着型軽費老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_362.csv',True),
    ('介護','364_地域密着型特定施設入居者生活介護（サービス付き高齢者向け住宅）','地域密着型サービス付き高齢者向け住宅','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_364.csv',True),
    ('介護','410_特定福祉用具販売','福祉用具販売','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_410.csv',False),
    ('介護','430_居宅介護支援','ケアマネジャー・居宅介護支援','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_430.csv',True),
    ('介護','510_介護老人福祉施設','特別養護老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_510.csv',True),
    ('介護','520_介護老人保健施設','介護老人保健施設','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_520.csv',True),
    ('介護','530_介護療養型医療施設','介護療養型医療施設','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_530.csv',True),
    ('介護','540_地域密着型介護老人福祉施設入所者生活介護','地域密着型特別養護老人ホーム','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_540.csv',True),
    ('介護','550_介護医療院','介護医療院','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_550.csv',True),
    ('介護','710_夜間対応型訪問介護','夜間対応型訪問介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_710.csv',False),
    ('介護','720_認知症対応型通所介護','認知症対応型デイサービス','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_720.csv',True),
    ('介護','730_小規模多機能型居宅介護','小規模多機能型居宅介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_730.csv',True),
    ('介護','760_定期巡回・随時対応型訪問介護看護','定期巡回・随時対応型訪問介護看護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_760.csv',True),
    ('介護','770_看護小規模多機能型居宅介護','看護小規模多機能型居宅介護','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_770.csv',True),
    ('介護','780_地域密着型通所介護','地域密着型デイサービス','2025-12末','https://www.mhlw.go.jp/content/12300000/jigyosho_780.csv',True),
]

NAME_KEYS = ['事業所名','施設名称','医療機関名称','医療機関名','薬局名称','助産所名称','名称','name']
PREF_KEYS = ['都道府県','都道府県名','所在地都道府県','所在地_都道府県','住所都道府県','pref']
CITY_KEYS = ['市区町村','市町村','市町村名','所在地市区町村','所在地_市区町村','住所市区町村','city']
ADDRESS_KEYS = ['所在地','住所','所在地住所','所在地_住所','所在地詳細','address']
PHONE_KEYS = ['電話番号','電話','連絡先電話番号','phone','TEL','tel']
URL_KEYS = ['URL','url','ホームページ','ホームページアドレス','ウェブサイト','法人ホームページ']
ID_KEYS = ['介護サービス事業所番号','事業所番号','医療機関番号','機関コード','ID','id']

def norm(s):
    return re.sub(r'[\s　()（）・_\-]+','', str(s or '').strip().lower())

def pick(row, keys):
    if not row:
        return ''
    # direct match
    for k in keys:
        if k in row and row.get(k) not in (None, ''):
            return str(row.get(k)).strip()
    # normalized contains match
    nmap = {norm(k): k for k in row.keys()}
    for wanted in keys:
        nw = norm(wanted)
        for nk, orig in nmap.items():
            if nw == nk or nw in nk or nk in nw:
                val = row.get(orig)
                if val not in (None, ''):
                    return str(val).strip()
    return ''

def get_city_from_address(address):
    if not address:
        return ''
    m = re.search(r'([一-龥ぁ-んァ-ヶA-Za-z0-9]+市|[一-龥ぁ-んァ-ヶA-Za-z0-9]+区|[一-龥ぁ-んァ-ヶA-Za-z0-9]+町|[一-龥ぁ-んァ-ヶA-Za-z0-9]+村)', address)
    return m.group(1) if m else ''

def get_pref_from_address(address):
    prefs = '北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split()
    for p in prefs:
        if address and p in address:
            return p
    return ''

def read_csv_bytes(data):
    for enc in ['utf-8-sig','utf-8','cp932']:
        try:
            text = data.decode(enc)
            return list(csv.DictReader(io.StringIO(text)))
        except UnicodeDecodeError:
            continue
    text = data.decode('utf-8', errors='replace')
    return list(csv.DictReader(io.StringIO(text)))

def download(url):
    print('download:', url, file=sys.stderr)
    with urllib.request.urlopen(url, timeout=90) as r:
        return r.read()

def iter_rows_from_url(url):
    data = download(url)
    if url.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.lower().endswith('.csv'):
                    yield from read_csv_bytes(z.read(name))
    else:
        yield from read_csv_bytes(data)

def make_tags(category, ftype):
    tags = [category, ftype]
    if any(x in ftype for x in ['病院','介護医療院','訪問看護','看護小規模']): tags.append('医療')
    if any(x in ftype for x in ['老健','介護老人保健施設','リハビリ','通所リハ']): tags.append('リハビリ')
    if any(x in ftype for x in ['認知症','グループホーム']): tags.append('認知症')
    if any(x in ftype for x in ['有料老人ホーム','サービス付き高齢者向け住宅','特別養護老人ホーム','介護老人福祉施設','介護医療院']): tags.append('入所')
    if any(x in ftype for x in ['ショート','短期入所']): tags.append('一時利用')
    if any(x in ftype for x in ['居宅介護支援','ケアマネ']): tags.append('相談')
    return ','.join(dict.fromkeys(tags))

def desc(ftype):
    base = {
        '病院':'入院・治療・退院支援の相談先になる医療機関です。退院先の調整は担当看護師や医療相談員に確認してください。',
        '特別養護老人ホーム':'常時介護が必要で在宅生活が難しい方の生活の場となる施設です。入所条件や待機状況を確認します。',
        '介護老人保健施設':'病院退院後すぐ自宅へ戻るのが不安な場合に、リハビリをしながら在宅復帰を目指す施設です。',
        '介護医療院':'長期的な医療管理と介護の両方が必要な方の入所施設です。',
        'グループホーム':'認知症のある方が少人数で生活する施設です。要支援・要介護度や地域要件を確認します。',
        'ケアマネジャー・居宅介護支援':'介護サービスの計画作成や事業所調整を行う相談先です。退院後の生活準備で重要です。',
        '訪問看護':'看護師などが自宅へ訪問し、健康状態の確認や医療的ケア、療養生活の支援を行います。',
        'デイサービス':'日中に通って食事・入浴・機能訓練・見守りなどを受けるサービスです。',
        'ショートステイ':'家族の休息や一時的な受け入れが必要な時に短期間利用するサービスです。',
    }
    for k,v in base.items():
        if k in ftype: return v
    return f'{ftype}の公式オープンデータから取り込んだ候補です。詳細は公式情報・電話・見学で確認してください。'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['core','all'], default='core')
    ap.add_argument('--pref', default='', help='例: 埼玉県。空なら全国')
    ap.add_argument('--output', default='facilities.csv')
    args = ap.parse_args()

    selected = [s for s in SOURCES if args.mode == 'all' or s[5]]
    seen = set()
    out_fields = ['name','type','pref','city','tags','description','url','address','phone','source','source_url','last_updated','external_search']
    count = 0
    with open(args.output, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for category, dataset, ftype, date, url, recommended in selected:
            try:
                for row in iter_rows_from_url(url):
                    name = pick(row, NAME_KEYS)
                    address = pick(row, ADDRESS_KEYS)
                    pref = pick(row, PREF_KEYS) or get_pref_from_address(address)
                    city = pick(row, CITY_KEYS) or get_city_from_address(address)
                    if args.pref and pref != args.pref:
                        continue
                    if not name:
                        continue
                    phone = pick(row, PHONE_KEYS)
                    home = pick(row, URL_KEYS)
                    fid = pick(row, ID_KEYS)
                    key = (name, ftype, pref, city, address, phone, fid)
                    if key in seen:
                        continue
                    seen.add(key)
                    external_search = f'https://www.google.com/search?q={urllib.request.quote(name + " " + (city or pref or ""))}'
                    w.writerow({
                        'name': name,
                        'type': ftype,
                        'pref': pref,
                        'city': city,
                        'tags': make_tags(category, ftype),
                        'description': desc(ftype),
                        'url': home or external_search,
                        'address': address,
                        'phone': phone,
                        'source': '厚生労働省オープンデータ',
                        'source_url': url,
                        'last_updated': date,
                        'external_search': external_search,
                    })
                    count += 1
            except Exception as e:
                print('ERROR:', dataset, url, e, file=sys.stderr)
    print(f'done: {args.output} ({count} rows)', file=sys.stderr)

if __name__ == '__main__':
    main()
