-- Annotate historical trades that failed the 2026-11-27 price/calendar audit.
-- The ledger is immutable: this migration only adds provenance columns and
-- backfills the 103 affected rows (98 non-trading-day fills, 5 out-of-range fills).

ALTER TABLE public.trades ADD COLUMN IF NOT EXISTS audit_flag TEXT;
ALTER TABLE public.trades ADD COLUMN IF NOT EXISTS audit_note TEXT;

COMMENT ON COLUMN public.trades.audit_flag IS
    'Audit annotation: NON_TRADING_DAY or PRICE_OUTSIDE_DAY_RANGE. NULL means the trade passed the price/calendar audit.';
COMMENT ON COLUMN public.trades.audit_note IS
    'Human-readable evidence for audit_flag (session date, recorded price, and the OHLC range it violates).';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'trades_audit_flag_check') THEN
        ALTER TABLE public.trades
            ADD CONSTRAINT trades_audit_flag_check
            CHECK (audit_flag IS NULL OR audit_flag IN ('NON_TRADING_DAY', 'PRICE_OUTSIDE_DAY_RANGE'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS trades_audit_flag_idx
    ON public.trades (audit_flag)
    WHERE audit_flag IS NOT NULL;

UPDATE public.trades AS t
SET audit_flag = v.flag,
    audit_note = v.note
FROM (VALUES
    ('3f7d2b7a-bdb1-43e9-b712-f949fa29ca95', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.9650 has no same-day OHLC bar.'),
    ('2f1bdbfb-eab1-41f4-959d-8ffbdd5cce48', 'PRICE_OUTSIDE_DAY_RANGE', 'Fill 83.0415 is 9.96% outside the 2026-11-19 session range [92.72, 115.10]; price matches a later session.'),
    ('638138fd-ae0b-478d-9725-4e2fa4bda2c4', 'PRICE_OUTSIDE_DAY_RANGE', 'Fill 83.0415 is 9.96% outside the 2026-11-19 session range [92.72, 115.10]; price matches a later session.'),
    ('4b629e83-63cf-49ab-a9cc-37e05188aecf', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 136.5232 has no same-day OHLC bar.'),
    ('bb080588-e3f5-499a-9cbd-7246ec962766', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 633.8666 has no same-day OHLC bar.'),
    ('b432cff0-3187-49f3-b319-613c84e4cc6f', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 101.1800 has no same-day OHLC bar.'),
    ('7f5418f0-59b9-47b7-95f1-0f06560cbe3c', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 582.2200 has no same-day OHLC bar.'),
    ('f8086414-c5d8-438d-acff-dfc0f737f07f', 'PRICE_OUTSIDE_DAY_RANGE', 'Fill 83.0415 is 9.96% outside the 2026-11-19 session range [92.72, 115.10]; price matches a later session.'),
    ('fb6966c2-7ea3-4215-ab1b-280ed3182345', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 131.2800 has no same-day OHLC bar.'),
    ('39f30cdc-15fe-4395-ad7b-e52626ef418d', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 171.3600 has no same-day OHLC bar.'),
    ('b001ded0-0204-42af-a5be-6fcef4c6337d', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 156.8700 has no same-day OHLC bar.'),
    ('19d0d7ba-1aa4-4453-8a71-9972fb873406', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 354.3600 has no same-day OHLC bar.'),
    ('d1a8ff83-af3d-4011-8a27-d34ca07822db', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 82.2400 has no same-day OHLC bar.'),
    ('f93b1de5-d7df-41cf-b8bf-b55aa2f12d80', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 158.1650 has no same-day OHLC bar.'),
    ('e3675ae4-cc1d-47eb-b256-280e83b7ac04', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 118.6793 has no same-day OHLC bar.'),
    ('40162557-694b-4adf-b1fa-464e99dae92c', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 118.6793 has no same-day OHLC bar.'),
    ('97033457-5cf9-4523-8b37-91aaa1bbbedc', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 143.9480 has no same-day OHLC bar.'),
    ('4aa22095-8c48-417d-a122-c7adb6f33970', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 39.1104 has no same-day OHLC bar.'),
    ('54154cf7-4381-4fa1-bc96-a34bf740068e', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 143.9480 has no same-day OHLC bar.'),
    ('000a6d06-460f-471a-9c22-5d95fa9a9113', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.9650 has no same-day OHLC bar.'),
    ('fa8a3195-bd19-4cf6-942a-901caaaa02fd', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.7199 has no same-day OHLC bar.'),
    ('a3a27258-5c08-4c80-9bf1-53b0a8110207', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 136.5232 has no same-day OHLC bar.'),
    ('34caea03-b944-4670-8b8b-b645c1a2adb1', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.7199 has no same-day OHLC bar.'),
    ('a81202d9-1ef0-42b1-8eff-03bd4a335310', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.9650 has no same-day OHLC bar.'),
    ('7448fbeb-47b6-4dc8-9ec4-de04a7e3db70', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 62.6487 has no same-day OHLC bar.'),
    ('e4aaf3d8-6125-403a-aa0f-155a9d7f1e96', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 171.0744 has no same-day OHLC bar.'),
    ('4bbacf67-79d3-429c-b7bd-c69b1e4758fc', 'NON_TRADING_DAY', 'Executed 2026-08-23 (Sunday, weekend) with no US equity session. Recorded price 174.7873 has no same-day OHLC bar.'),
    ('71249296-082e-4fa7-aa16-4e93fd05171b', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 163.7281 has no same-day OHLC bar.'),
    ('72dd6527-ca23-43b8-86c4-da726df74b72', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 64.0280 has no same-day OHLC bar.'),
    ('08678a01-462c-4f27-876b-ea22ab49af1e', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 57.2214 has no same-day OHLC bar.'),
    ('cd857e2a-d710-4e4a-9666-f6cb622ce6d8', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 162.5812 has no same-day OHLC bar.'),
    ('246485ea-36ce-4129-ac03-16fe7bd6063b', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 63.9920 has no same-day OHLC bar.'),
    ('0c0cde37-c451-4309-89e6-dd178d8cdf24', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 58.1290 has no same-day OHLC bar.'),
    ('2f777de1-197a-4bf8-9aa1-6e7a899c8541', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 113.5732 has no same-day OHLC bar.'),
    ('cb70ddc6-8fb8-470d-aedf-497af07d396e', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 112.0860 has no same-day OHLC bar.'),
    ('b07aefcf-6f42-44be-abdc-c457ba104131', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 190.8054 has no same-day OHLC bar.'),
    ('5451dfd8-0e5f-4536-ae6b-64cecf5a0f93', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 190.8054 has no same-day OHLC bar.'),
    ('4eedb321-ce64-4ef8-aae0-f34c768f213e', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 163.8919 has no same-day OHLC bar.'),
    ('1637eada-a93e-48ee-9bbb-57254eb74cc1', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 113.5732 has no same-day OHLC bar.'),
    ('102ef837-92d4-40d7-abfd-62a52c20ab02', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 65.1074 has no same-day OHLC bar.'),
    ('5c42569c-161b-4c95-9089-c3068d1c2224', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 113.5732 has no same-day OHLC bar.'),
    ('d88ed754-37bd-42b6-b19d-8668b20fd608', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 113.5732 has no same-day OHLC bar.'),
    ('91870663-7103-49ce-9c26-2ca2d56623c5', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 195.6221 has no same-day OHLC bar.'),
    ('3735c4b0-f74f-45ce-92c7-ff74d22ce670', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 112.5437 has no same-day OHLC bar.'),
    ('6c0505fb-a519-4101-b154-da53b043da87', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 195.6221 has no same-day OHLC bar.'),
    ('112ab46e-d76e-404e-b93c-2465227a4650', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 156.1219 has no same-day OHLC bar.'),
    ('aed8f223-5cc3-47b5-8008-adc8b806729b', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 64.0920 has no same-day OHLC bar.'),
    ('9c373c1c-8223-4232-837f-1b96c3837397', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 118.6793 has no same-day OHLC bar.'),
    ('beff6fa1-f23c-4f94-9162-8214d035044d', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 118.6793 has no same-day OHLC bar.'),
    ('71da06cf-a3eb-44b9-8468-a7dde2010536', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 64.2778 has no same-day OHLC bar.'),
    ('af117011-168f-4909-9f66-5d06fcf510f7', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 190.5147 has no same-day OHLC bar.'),
    ('987b3083-7c53-4bc8-a632-b8cafda08791', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 108.6257 has no same-day OHLC bar.'),
    ('c9aa2757-449d-4b17-80c5-e2687798eb85', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 190.5147 has no same-day OHLC bar.'),
    ('51ed021e-fe32-4662-b50e-aa1e57bdc4da', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 572.7135 has no same-day OHLC bar.'),
    ('d15f7eb4-bea6-42c7-8d4f-4ac21cc8033c', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 190.5147 has no same-day OHLC bar.'),
    ('cd3d7f4e-83ab-480b-95a5-3bd32fed8b18', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 64.2778 has no same-day OHLC bar.'),
    ('fbff7b37-8e98-4f83-9719-3651b75a9cad', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 156.6416 has no same-day OHLC bar.'),
    ('02630892-fae0-4ba5-8ae9-d3c85054e0bd', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 108.6257 has no same-day OHLC bar.'),
    ('7ad1a376-b082-4193-a875-857c5c0a1b13', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 193.5667 has no same-day OHLC bar.'),
    ('9dec4f1c-2c7c-4246-b05c-c40d0816c518', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 541.7708 has no same-day OHLC bar.'),
    ('d611909e-dff7-4433-939b-8a6d71dd2ef7', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 193.5667 has no same-day OHLC bar.'),
    ('ca9be938-d0e1-4906-a3eb-96376493a500', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 64.5623 has no same-day OHLC bar.'),
    ('d422c1af-e9af-4039-8d25-f1438ee9a3b8', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 193.5667 has no same-day OHLC bar.'),
    ('879f4af2-0b71-4b0e-b7ea-0d74e44cfd22', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 110.2251 has no same-day OHLC bar.'),
    ('9f2821f1-cd65-464c-a477-7e9ef882da43', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 157.6788 has no same-day OHLC bar.'),
    ('442a0be9-d4fd-487c-993a-7778ac725f89', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 64.5623 has no same-day OHLC bar.'),
    ('8a3183b8-5899-40dd-84e7-98115349a2b1', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 110.2251 has no same-day OHLC bar.'),
    ('132a4ed3-609c-4767-a905-a337da6cdcde', 'NON_TRADING_DAY', 'Executed 2026-08-23 (Sunday, weekend) with no US equity session. Recorded price 63.1416 has no same-day OHLC bar.'),
    ('ac8fedf3-c6d1-4463-a46d-fd3e9f1d2478', 'PRICE_OUTSIDE_DAY_RANGE', 'Fill 54.5573 is 2.08% outside the 2026-09-21 session range [55.72, 56.21]; price matches a later session.'),
    ('42a2d489-7a79-460c-b443-32a7a8e14ba7', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 556.3517 has no same-day OHLC bar.'),
    ('32988768-8017-425b-8422-b5a5b4690f81', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 186.4068 has no same-day OHLC bar.'),
    ('3ab97962-05f4-49a8-ae71-d7d68b9b0b9b', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 136.5232 has no same-day OHLC bar.'),
    ('98eb7393-1b06-47f7-bf34-fd5dae65aea4', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 243.2816 has no same-day OHLC bar.'),
    ('f05ecb29-982d-42b8-b1bc-d9e73f0427e2', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 136.5232 has no same-day OHLC bar.'),
    ('716294cd-67ef-45c9-8c78-5fc4b619bd34', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.9650 has no same-day OHLC bar.'),
    ('26558c17-4b1e-4ea5-a023-c9d8462543d9', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 29.7199 has no same-day OHLC bar.'),
    ('26fa5c4e-8d28-4a85-b15e-2e4e69e7df38', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 97.1000 has no same-day OHLC bar.'),
    ('70b24b27-2bb9-4207-a2ec-1377f37e0535', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 131.2400 has no same-day OHLC bar.'),
    ('1d6d420e-7014-4973-a6a6-432f59a6d35e', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 527.2300 has no same-day OHLC bar.'),
    ('a0613f51-0aa6-46e6-9c16-cf0349229854', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 143.9480 has no same-day OHLC bar.'),
    ('9ef273f6-4098-4fe7-bbd2-38b3773e65ea', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 39.1104 has no same-day OHLC bar.'),
    ('2744c4a5-c2a2-4daf-847f-2aba46381985', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 317.8510 has no same-day OHLC bar.'),
    ('84fe0779-37cc-4663-b89e-89d66453570e', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 143.9480 has no same-day OHLC bar.'),
    ('93cb3804-6548-4ba5-a6a4-7a19e50e3f75', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 553.3866 has no same-day OHLC bar.'),
    ('3b23a14c-caf1-488b-875d-976481f33235', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 42.7514 has no same-day OHLC bar.'),
    ('63fbf734-1187-4d83-86f6-8abe9ef1f51c', 'NON_TRADING_DAY', 'Executed 2026-08-23 (Sunday, weekend) with no US equity session. Recorded price 546.5266 has no same-day OHLC bar.'),
    ('5c17fbb3-de6f-478e-98a7-129a9362c7e2', 'NON_TRADING_DAY', 'Executed 2026-08-23 (Sunday, weekend) with no US equity session. Recorded price 43.1984 has no same-day OHLC bar.'),
    ('d866dc91-cc08-4949-81c9-a422feadf850', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 567.2935 has no same-day OHLC bar.'),
    ('81f6b134-e476-4688-a9b8-32b3598a01a0', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 187.3736 has no same-day OHLC bar.'),
    ('c2753049-f734-422b-adb2-0a9d901a3321', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 43.1015 has no same-day OHLC bar.'),
    ('b3286940-73e0-49ee-a7e9-54c16b481a85', 'NON_TRADING_DAY', 'Executed 2026-08-30 (Sunday, weekend) with no US equity session. Recorded price 42.2089 has no same-day OHLC bar.'),
    ('b4b152ec-52de-49ce-9f0a-d7daa0b8aac6', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 42.4112 has no same-day OHLC bar.'),
    ('03c49b44-c732-4013-84a7-aed8835ab350', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 169.8349 has no same-day OHLC bar.'),
    ('d82a0a3c-a1b3-4981-98b1-f8d553724f47', 'NON_TRADING_DAY', 'Executed 2026-09-20 (Sunday, weekend) with no US equity session. Recorded price 41.1206 has no same-day OHLC bar.'),
    ('4396a498-c09f-4279-a704-2089864cc461', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 169.8450 has no same-day OHLC bar.'),
    ('a017115b-4e09-4e12-9ee3-08ce2d8048a0', 'NON_TRADING_DAY', 'Executed 2026-09-13 (Sunday, weekend) with no US equity session. Recorded price 41.7991 has no same-day OHLC bar.'),
    ('4a70fd8f-6547-497e-acf2-77d9dcfcc04d', 'NON_TRADING_DAY', 'Executed 2026-09-06 (Sunday, weekend) with no US equity session. Recorded price 43.0585 has no same-day OHLC bar.'),
    ('1adecd45-f047-4aa6-9e39-9c98d766f663', 'PRICE_OUTSIDE_DAY_RANGE', 'Fill 39.6901 is 2.19% outside the 2026-09-21 session range [40.58, 40.93]; price matches a later session.'),
    ('1b0e9300-93dc-4f75-8bad-e76937a96213', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 39.1104 has no same-day OHLC bar.'),
    ('1ae04b30-a5af-4298-93f2-2ec9499409a3', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 317.8510 has no same-day OHLC bar.'),
    ('808204dd-44f9-437f-942b-56f25e2160c7', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 286.4767 has no same-day OHLC bar.'),
    ('50811f5a-1369-4b2a-bf50-dc8bd41e02dd', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 39.1104 has no same-day OHLC bar.'),
    ('ddf45feb-d316-4983-bafa-fd61f0cf37a9', 'NON_TRADING_DAY', 'Executed 2026-11-26 (Thursday, US market holiday) with no US equity session. Recorded price 317.8510 has no same-day OHLC bar.')
) AS v(id, flag, note)
WHERE t.id = v.id::uuid;

NOTIFY pgrst, 'reload schema';
