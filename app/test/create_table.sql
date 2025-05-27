-- 1. 删除现有表（按依赖关系顺序删除）
DROP TABLE IF EXISTS task_tag_relations CASCADE;
DROP TABLE IF EXISTS task_records CASCADE;
DROP TABLE IF EXISTS tags CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;

-- 2. 删除现有的触发器函数（如果存在）
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
DROP FUNCTION IF EXISTS update_tasks_updated_time() CASCADE;
DROP FUNCTION IF EXISTS update_tags_updated_time() CASCADE;

-- =============================================
-- 优化后的数据库表创建脚本
-- 基于业务规则：一商户一应用，一对一密钥，一回调地址
-- =============================================

-- 1. 创建 merchants 表（强化唯一性约束）
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    merchant_id VARCHAR(50) NOT NULL UNIQUE,
    app_key VARCHAR(100) NOT NULL UNIQUE,
    app_secret VARCHAR(200) NOT NULL,
    callback_address VARCHAR(500) NOT NULL UNIQUE,
    password VARCHAR(255),
    user_source VARCHAR(10) NOT NULL DEFAULT 'U01',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 添加注释
    CONSTRAINT chk_merchant_id_not_empty CHECK (LENGTH(TRIM(merchant_id)) > 0),
    CONSTRAINT chk_app_key_not_empty CHECK (LENGTH(TRIM(app_key)) > 0),
    CONSTRAINT chk_app_secret_not_empty CHECK (LENGTH(TRIM(app_secret)) > 0),
    CONSTRAINT chk_callback_address_not_empty CHECK (LENGTH(TRIM(callback_address)) > 0),
    CONSTRAINT chk_user_source_valid CHECK (user_source IN ('U01', 'U02', 'U03'))
);

-- 为 merchants 表创建索引
CREATE INDEX idx_merchants_merchant_id ON merchants(merchant_id);
CREATE INDEX idx_merchants_app_key ON merchants(app_key);
CREATE INDEX idx_merchants_callback_address ON merchants(callback_address);
CREATE INDEX idx_merchants_is_active ON merchants(is_active);

-- 添加表注释
COMMENT ON TABLE merchants IS '商户信息表';
COMMENT ON COLUMN merchants.id IS '主键ID';
COMMENT ON COLUMN merchants.merchant_id IS '商户唯一标识';
COMMENT ON COLUMN merchants.app_key IS '应用密钥，全局唯一';
COMMENT ON COLUMN merchants.app_secret IS '应用秘钥，加密存储';
COMMENT ON COLUMN merchants.callback_address IS '回调地址，全局唯一';
COMMENT ON COLUMN merchants.password IS '商户密码，可为空';
COMMENT ON COLUMN merchants.user_source IS '用户来源';
COMMENT ON COLUMN merchants.is_active IS '是否激活';

-- 2. 创建 tasks 表
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    task_name VARCHAR(255) NOT NULL,
    trigger_method VARCHAR(50),
    port INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cron_expression VARCHAR(100),

    -- 添加约束
    CONSTRAINT chk_task_name_not_empty CHECK (LENGTH(TRIM(task_name)) > 0),
    CONSTRAINT chk_task_status_valid CHECK (status IN ('active', 'inactive', 'deleted')),
    CONSTRAINT chk_trigger_method_valid CHECK (trigger_method IN ('cron', 'manual', 'api') OR trigger_method IS NULL),
    CONSTRAINT chk_port_valid CHECK (port IS NULL OR (port > 0 AND port <= 65535))
);

-- 为 tasks 表创建索引
CREATE INDEX idx_tasks_task_name ON tasks(task_name);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_trigger_method ON tasks(trigger_method);

-- 添加表注释
COMMENT ON TABLE tasks IS '任务信息表';
COMMENT ON COLUMN tasks.task_id IS '任务ID';
COMMENT ON COLUMN tasks.task_name IS '任务名称';
COMMENT ON COLUMN tasks.trigger_method IS '触发方式：cron/manual/api';
COMMENT ON COLUMN tasks.port IS '端口号';
COMMENT ON COLUMN tasks.status IS '任务状态：active/inactive/deleted';
COMMENT ON COLUMN tasks.cron_expression IS 'cron表达式';

-- 3. 创建 tags 表（增强约束）
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(100) NOT NULL,
    parent_id INTEGER,
    tag_level INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (parent_id) REFERENCES tags(tag_id) ON DELETE SET NULL,

    -- 复合唯一约束：同一父级下标签名称不能重复
    CONSTRAINT uk_tag_name_parent UNIQUE (tag_name, parent_id),

    -- 检查约束
    CONSTRAINT chk_tag_name_not_empty CHECK (LENGTH(TRIM(tag_name)) > 0),
    CONSTRAINT chk_tag_level_valid CHECK (tag_level > 0 AND tag_level <= 10),
    CONSTRAINT chk_tag_status_valid CHECK (status IN ('active', 'inactive'))
);

-- 为 tags 表创建索引
CREATE INDEX idx_tags_tag_name ON tags(tag_name);
CREATE INDEX idx_tags_parent_id ON tags(parent_id);
CREATE INDEX idx_tags_status ON tags(status);
CREATE INDEX idx_tags_level ON tags(tag_level);

-- 添加表注释
COMMENT ON TABLE tags IS '标签信息表';
COMMENT ON COLUMN tags.tag_id IS '标签ID';
COMMENT ON COLUMN tags.tag_name IS '标签名称';
COMMENT ON COLUMN tags.parent_id IS '父标签ID';
COMMENT ON COLUMN tags.tag_level IS '标签层级';
COMMENT ON COLUMN tags.status IS '标签状态：active/inactive';

-- 4. 创建 task_records 表（增加错误信息字段）
CREATE TABLE task_records (
    record_id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    trigger_method VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    execution_status VARCHAR(20),
    error_message VARCHAR(1000),
    created_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,

    -- 检查约束
    CONSTRAINT chk_execution_status_valid CHECK (execution_status IN ('success', 'failed', 'running') OR execution_status IS NULL),
    CONSTRAINT chk_end_time_after_start CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time)
);

-- 为 task_records 表创建索引
CREATE INDEX idx_task_records_task_id ON task_records(task_id);
CREATE INDEX idx_task_records_execution_status ON task_records(execution_status);
CREATE INDEX idx_task_records_created_time ON task_records(created_time);
CREATE INDEX idx_task_records_start_time ON task_records(start_time);

-- 添加表注释
COMMENT ON TABLE task_records IS '任务执行记录表';
COMMENT ON COLUMN task_records.record_id IS '记录ID';
COMMENT ON COLUMN task_records.task_id IS '任务ID';
COMMENT ON COLUMN task_records.trigger_method IS '触发方式';
COMMENT ON COLUMN task_records.execution_status IS '执行状态：success/failed/running';
COMMENT ON COLUMN task_records.error_message IS '错误信息';

-- 5. 创建 task_tag_relations 表（防止重复关联）
CREATE TABLE task_tag_relations (
    relation_id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE,

    -- 复合唯一约束：防止重复关联
    CONSTRAINT uk_task_tag_relation UNIQUE (task_id, tag_id)
);

-- 为 task_tag_relations 表创建索引
CREATE INDEX idx_task_tag_relations_task_id ON task_tag_relations(task_id);
CREATE INDEX idx_task_tag_relations_tag_id ON task_tag_relations(tag_id);

-- 添加表注释
COMMENT ON TABLE task_tag_relations IS '任务标签关联表';
COMMENT ON COLUMN task_tag_relations.relation_id IS '关系ID';
COMMENT ON COLUMN task_tag_relations.task_id IS '任务ID';
COMMENT ON COLUMN task_tag_relations.tag_id IS '标签ID';

-- =============================================
-- 创建触发器函数和触发器
-- =============================================

-- 创建更新时间的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为 merchants 表添加更新时间触发器
CREATE TRIGGER update_merchants_updated_at
    BEFORE UPDATE ON merchants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 为 tasks 表添加更新时间触发器
CREATE OR REPLACE FUNCTION update_tasks_updated_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_time
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_tasks_updated_time();

-- 为 tags 表添加更新时间触发器
CREATE OR REPLACE FUNCTION update_tags_updated_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tags_updated_time
    BEFORE UPDATE ON tags
    FOR EACH ROW
    EXECUTE FUNCTION update_tags_updated_time();

-- =============================================
-- 插入示例数据（可选）
-- =============================================

-- 插入示例商户数据
INSERT INTO merchants (merchant_id, app_key, app_secret, callback_address, user_source)
VALUES
    ('MERCHANT_001', 'app_key_001', 'encrypted_secret_001', 'https://api.example1.com/callback', 'U01'),
    ('MERCHANT_002', 'app_key_002', 'encrypted_secret_002', 'https://api.example2.com/callback', 'U01');

-- 插入示例标签数据
INSERT INTO tags (tag_name, tag_level)
VALUES
    ('系统任务', 1),
    ('业务任务', 1),
    ('定时任务', 1);

INSERT INTO tags (tag_name, parent_id, tag_level)
VALUES
    ('数据同步', 1, 2),
    ('数据清理', 1, 2),
    ('订单处理', 2, 2);

-- 插入示例任务数据
INSERT INTO tasks (task_name, trigger_method, status, cron_expression)
VALUES
    ('每日数据同步', 'cron', 'active', '0 0 2 * * ?'),
    ('手动数据导出', 'manual', 'active', NULL),
    ('API触发处理', 'api', 'active', NULL);

-- =============================================
-- 查询验证脚本
-- =============================================

-- 查看所有表
-- \dt

-- 查看表结构
-- \d merchants
-- \d tasks
-- \d tags
-- \d task_records
-- \d task_tag_relations

-- 验证约束
-- SELECT constraint_name, constraint_type FROM information_schema.table_constraints WHERE table_name = 'merchants';

-- 验证数据
-- SELECT * FROM merchants;
-- SELECT * FROM tags;
-- SELECT * FROM tasks;