#!/usr/bin/env python3
"""
Database initialization script with versioning schema
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'testcase_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

class DatabaseInitializer:
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Connect to database"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.connection.cursor()
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
    
    def execute_sql(self, sql: str, description: str = ""):
        """Execute SQL statement"""
        try:
            self.cursor.execute(sql)
            if description:
                logger.info(f"✅ {description}")
        except Exception as e:
            logger.error(f"❌ Failed to execute SQL: {e}")
            logger.error(f"SQL: {sql}")
            raise
    
    def drop_existing_tables(self):
        """Drop existing tables"""
        logger.info("🗑️  Dropping existing tables...")
        
        tables = [
            'usage',
            'subscriptions',
            'plans',
            'traceability_matrix',
            'tcm_testcase_mappings',
            'testcase_section_map',
            'sections',
            'xray_projects',
            'zephyr_projects',
            'testrail_suites',
            'testrail_projects',
            'tcm_credentials',
            'tcm_integrations',
            'requirement_testcase_map',
            'testcases', 
            'requirements',
            'requirement_labels',
            'users',
            'tenants'
        ]
        
        for table in tables:
            self.execute_sql(f"DROP TABLE IF EXISTS {table} CASCADE;", f"Dropped {table}")
    
    def create_tenants_table(self):
        """Create tenants table"""
        logger.info("🏢 Creating tenants table...")
        
        sql = """
        CREATE TABLE tenants (
            tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_name TEXT NOT NULL,
            tenant_type TEXT NOT NULL CHECK (tenant_type IN ('PERSONAL','ORGANIZATION')),
            tenant_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (tenant_state IN ('ACTIVE','PENDING')),
            primary_domain TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created tenants table")
    
    def create_requirement_labels_table(self):
        """Create requirement_labels table"""
        logger.info("🏷️  Creating requirement_labels table...")
        
        sql = """
        CREATE TABLE requirement_labels (
            label_id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            requirement_label VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tenant_id, requirement_label)
        );
        """
        self.execute_sql(sql, "Created requirement_labels table")
    
    def create_requirements_table(self):
        """Create requirements table with versioning"""
        logger.info("📋 Creating requirements table...")
        
        sql = """
        CREATE TABLE requirements (
            requirement_id UUID NOT NULL,
            row_id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            label_id INTEGER NOT NULL REFERENCES requirement_labels(label_id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            version INTEGER NOT NULL,
            raw_text TEXT,
            requirement_detail JSON NOT NULL,
            testcase_generation_status TEXT CHECK (
                testcase_generation_status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'SYNCHED')
            ) DEFAULT 'NOT_STARTED',
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            meta_info JSON,
            UNIQUE(requirement_id, version)
        );
        """
        self.execute_sql(sql, "Created requirements table")
    
    def create_testcases_table(self):
        """Create testcases table with versioning"""
        logger.info("🧪 Creating testcases table...")
        
        sql = """
        CREATE TABLE testcases (
            testcase_id UUID NOT NULL,
            row_id BIGSERIAL PRIMARY KEY,
            requirement_id UUID NOT NULL,
            title TEXT NOT NULL,
            steps JSON NOT NULL,
            expected_result TEXT NOT NULL,
            status TEXT NOT NULL,
            sync_status TEXT CHECK (sync_status IN ('NEW','UPDATED','SYNCHED')) DEFAULT 'NEW',
            version INTEGER NOT NULL,
            priority TEXT DEFAULT 'MEDIUM',
            derived_from_row_id BIGINT REFERENCES testcases(row_id),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            meta_info JSON,
            UNIQUE(testcase_id, version)
        );
        """
        self.execute_sql(sql, "Created testcases table")

    def create_sections_table(self):
        """Create sections table (canonical internal/external sections)."""
        logger.info("📚 Creating sections table...")

        sql = """
        CREATE TABLE sections (
            section_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            section_name TEXT NOT NULL,
            source TEXT CHECK (source IN ('internal','testrail','zephyr','xray')) DEFAULT 'internal',
            external_section_id TEXT,
            external_suite_id TEXT,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tenant_id, section_name)
        );
        """
        self.execute_sql(sql, "Created sections table")

    def create_testcase_section_map_table(self):
        """Create mapping between testcases and sections (many-to-many)."""
        logger.info("🧭 Creating testcase_section_map table...")

        sql = """
        CREATE TABLE testcase_section_map (
            map_id SERIAL PRIMARY KEY,
            testcase_id UUID NOT NULL,
            section_id UUID NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
            linked_at_version INTEGER NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(testcase_id, section_id, linked_at_version),
            FOREIGN KEY (testcase_id, linked_at_version)
                REFERENCES testcases(testcase_id, version) ON DELETE CASCADE
        );
        """
        self.execute_sql(sql, "Created testcase_section_map table")

    def create_tcm_testcase_mappings_table(self):
        """Create mapping between internal and external TCM testcases."""
        logger.info("🗺️  Creating tcm_testcase_mappings table...")

        sql = """
        CREATE TABLE tcm_testcase_mappings (
            mapping_id SERIAL PRIMARY KEY,
            testcase_id UUID NOT NULL,
            tcm_tool TEXT CHECK (tcm_tool IN ('testrail','zephyr','xray')) NOT NULL,
            external_testcase_id TEXT NOT NULL,
            sync_direction TEXT CHECK (sync_direction IN ('PUSH','PULL','BIDIRECTIONAL')) DEFAULT 'BIDIRECTIONAL',
            last_synced_at TIMESTAMPTZ,
            UNIQUE(testcase_id, tcm_tool)
        );
        """
        self.execute_sql(sql, "Created tcm_testcase_mappings table")
    
    def create_mapping_table(self):
        """Create requirement_testcase_map table"""
        logger.info("🔗 Creating requirement_testcase_map table...")
        
        sql = """
        CREATE TABLE requirement_testcase_map (
            id SERIAL PRIMARY KEY,
            requirement_id UUID NOT NULL,
            requirement_version INTEGER NOT NULL,
            testcase_id UUID NOT NULL,
            testcase_version INTEGER NOT NULL,
            linked_at_version INTEGER NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(requirement_id, requirement_version, testcase_id, testcase_version),
            FOREIGN KEY (requirement_id, requirement_version)
                REFERENCES requirements(requirement_id, version) ON DELETE CASCADE,
            FOREIGN KEY (testcase_id, testcase_version)
                REFERENCES testcases(testcase_id, version) ON DELETE CASCADE
        );
        """
        self.execute_sql(sql, "Created requirement_testcase_map table")
    
    def create_users_table(self):
        """Create users table (IAM schema)"""
        logger.info("👥 Creating users table...")
        
        sql = """
        CREATE TABLE users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            auth_provider TEXT NOT NULL DEFAULT 'GOOGLE' CHECK (auth_provider IN ('GOOGLE','LINKEDIN','LDAP','SAML','LOCAL','EMBEDDED')),
            external_subject TEXT,
            state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE','PENDING')),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created users table")
    
    def create_tcm_integrations_table(self):
        """Create TCM integrations table"""
        logger.info("🔌 Creating TCM integrations table...")
        
        sql = """
        CREATE TABLE tcm_integrations (
            integration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            integrator_type VARCHAR(50) NOT NULL CHECK (integrator_type IN ('testrail', 'zephyr', 'xray')),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created TCM integrations table")
    
    def create_tcm_credentials_table(self):
        """Create TCM credentials table"""
        logger.info("🔑 Creating TCM credentials table...")
        
        sql = """
        CREATE TABLE tcm_credentials (
            credential_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            integration_id UUID NOT NULL REFERENCES tcm_integrations(integration_id) ON DELETE CASCADE,
            base_url TEXT NOT NULL,
            api_key TEXT,
            username TEXT,
            password TEXT,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            CONSTRAINT check_auth_method CHECK (
                (api_key IS NOT NULL AND api_key != '') OR 
                (username IS NOT NULL AND username != '' AND password IS NOT NULL AND password != '')
            )
        );
        """
        self.execute_sql(sql, "Created TCM credentials table")
    
    def create_testrail_projects_table(self):
        """Create TestRail projects table"""
        logger.info("🚂 Creating TestRail projects table...")
        
        sql = """
        CREATE TABLE testrail_projects (
            project_id SERIAL PRIMARY KEY,
            integration_id UUID NOT NULL REFERENCES tcm_integrations(integration_id) ON DELETE CASCADE,
            external_project_id INTEGER NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            project_description TEXT,
            project_mode INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created TestRail projects table")
    
    def create_testrail_suites_table(self):
        """Create TestRail suites table"""
        logger.info("🏗️  Creating TestRail suites table...")
        
        sql = """
        CREATE TABLE testrail_suites (
            suite_id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES testrail_projects(project_id) ON DELETE CASCADE,
            external_suite_id INTEGER NOT NULL,
            suite_name VARCHAR(255) NOT NULL,
            suite_description TEXT,
            is_active BOOLEAN DEFAULT FALSE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(project_id, external_suite_id)
        );
        """
        self.execute_sql(sql, "Created TestRail suites table")
    
    def create_zephyr_projects_table(self):
        """Create Zephyr projects table"""
        logger.info("💨 Creating Zephyr projects table...")
        
        sql = """
        CREATE TABLE zephyr_projects (
            project_id SERIAL PRIMARY KEY,
            integration_id UUID NOT NULL REFERENCES tcm_integrations(integration_id) ON DELETE CASCADE,
            project_key VARCHAR(50) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            project_lead VARCHAR(255),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created Zephyr projects table")
    
    def create_xray_projects_table(self):
        """Create Xray projects table"""
        logger.info("🔍 Creating Xray projects table...")
        
        sql = """
        CREATE TABLE xray_projects (
            project_id SERIAL PRIMARY KEY,
            integration_id UUID NOT NULL REFERENCES tcm_integrations(integration_id) ON DELETE CASCADE,
            project_key VARCHAR(50) NOT NULL,
            project_name VARCHAR(255) NOT NULL,
            project_type VARCHAR(50),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_synced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created Xray projects table")
    
    def create_traceability_matrix_table(self):
        """Create traceability matrix table"""
        logger.info("🔗 Creating traceability matrix table...")
        
        sql = """
        CREATE TABLE traceability_matrix (
            matrix_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            requirement_id UUID NOT NULL,
            version INTEGER NOT NULL,
            status TEXT CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED')) DEFAULT 'NOT_STARTED',
            traceability_data JSON,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(requirement_id, version)
        );
        """
        self.execute_sql(sql, "Created traceability matrix table")
    
    def create_plans_table(self):
        """Create plans table for subscription management"""
        logger.info("📋 Creating plans table...")
        
        sql = """
        CREATE TABLE plans (
            plan_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            price VARCHAR(20) NOT NULL DEFAULT '0.00',
            duration VARCHAR(20) NOT NULL DEFAULT 'monthly',
            limits JSON NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """
        self.execute_sql(sql, "Created plans table")
    
    def create_subscriptions_table(self):
        """Create subscriptions table for tenant subscriptions"""
        logger.info("💳 Creating subscriptions table...")
        
        sql = """
        CREATE TABLE subscriptions (
            subscription_id SERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            plan_id INTEGER NOT NULL REFERENCES plans(plan_id),
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CANCELLED', 'EXPIRED')),
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ,
            auto_renew BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(tenant_id)
        );
        """
        self.execute_sql(sql, "Created subscriptions table")
    
    def create_usage_table(self):
        """Create usage table for tracking subscription limits"""
        logger.info("📊 Creating usage table...")
        
        sql = """
        CREATE TABLE usage (
            usage_id SERIAL PRIMARY KEY,
            subscription_id INTEGER NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
            metric VARCHAR(50) NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            "limit" INTEGER NOT NULL,
            reset_date TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
            UNIQUE(subscription_id, metric)
        );
        """
        self.execute_sql(sql, "Created usage table")
    
    def create_indexes(self):
        """Create indexes for performance"""
        logger.info("📊 Creating indexes...")
        
        indexes = [
            # Core tables indexes
            ("idx_requirement_labels_tenant_id", "requirement_labels(tenant_id)"),
            ("idx_requirement_labels_name", "requirement_labels(requirement_label)"),
            
            ("idx_requirements_requirement_id", "requirements(requirement_id)"),
            ("idx_requirements_label_id", "requirements(label_id)"),
            ("idx_requirements_tenant_id", "requirements(tenant_id)"),
            ("idx_requirements_version", "requirements(requirement_id, version)"),
            ("idx_requirements_label_id_version", "requirements(label_id, version)"),
            
            ("idx_testcases_testcase_id", "testcases(testcase_id)"),
            ("idx_testcases_requirement_id", "testcases(requirement_id)"),
            ("idx_testcases_version", "testcases(testcase_id, version)"),
            ("idx_testcases_derived_from", "testcases(derived_from_row_id)"),
            ("idx_testcases_req_id_version", "testcases(requirement_id, version)"),

            # Sections & mappings
            ("idx_sections_tenant_id", "sections(tenant_id)"),
            ("idx_sections_name", "sections(section_name)"),
            ("idx_tsm_testcase_id", "testcase_section_map(testcase_id)"),
            ("idx_tsm_section_id", "testcase_section_map(section_id)"),
            
            ("idx_map_requirement_id", "requirement_testcase_map(requirement_id)"),
            ("idx_map_testcase_id", "requirement_testcase_map(testcase_id)"),
            ("idx_map_requirement_version", "requirement_testcase_map(requirement_id, requirement_version)"),
            ("idx_map_testcase_version", "requirement_testcase_map(testcase_id, testcase_version)"),
            
            # IAM Indexes
            ("idx_users_tenant_id", "users(tenant_id)"),
            ("idx_users_email", "users(email)"),
            ("idx_users_auth_provider", "users(auth_provider)"),
            
            # TCM Indexes
            ("idx_tcm_integrations_tenant_id", "tcm_integrations(tenant_id)"),
            ("idx_tcm_integrations_integrator_type", "tcm_integrations(integrator_type)"),
            ("idx_tcm_credentials_integration_id", "tcm_credentials(integration_id)"),
            
            # TestRail Project Indexes
            ("idx_testrail_projects_integration_id", "testrail_projects(integration_id)"),
            ("idx_testrail_projects_external_id", "testrail_projects(external_project_id)"),
            ("idx_testrail_projects_is_active", "testrail_projects(is_active)"),
            ("idx_testrail_projects_mode", "testrail_projects(project_mode)"),
            
            # TestRail Suite Indexes
            ("idx_testrail_suites_project_id", "testrail_suites(project_id)"),
            ("idx_testrail_suites_external_id", "testrail_suites(external_suite_id)"),
            ("idx_testrail_suites_is_active", "testrail_suites(is_active)"),
            
            # Zephyr Project Indexes
            ("idx_zephyr_projects_integration_id", "zephyr_projects(integration_id)"),
            ("idx_zephyr_projects_project_key", "zephyr_projects(project_key)"),
            
            # Xray Project Indexes
            ("idx_xray_projects_integration_id", "xray_projects(integration_id)"),
            ("idx_xray_projects_project_key", "xray_projects(project_key)"),

            # TCM testcase mappings indexes
            ("idx_tcm_tc_mappings_tool", "tcm_testcase_mappings(tcm_tool)"),
            ("idx_tcm_tc_mappings_external", "tcm_testcase_mappings(external_testcase_id)"),
            
            # Traceability Matrix Indexes
            ("idx_traceability_matrix_requirement_id", "traceability_matrix(requirement_id)"),
            ("idx_traceability_matrix_version", "traceability_matrix(version)"),
            ("idx_traceability_matrix_status", "traceability_matrix(status)"),
            
            # Subscription Indexes
            ("idx_plans_name", "plans(name)"),
            ("idx_plans_is_active", "plans(is_active)"),
            ("idx_subscriptions_tenant_id", "subscriptions(tenant_id)"),
            ("idx_subscriptions_plan_id", "subscriptions(plan_id)"),
            ("idx_subscriptions_status", "subscriptions(status)"),
            ("idx_usage_subscription_id", "usage(subscription_id)"),
            ("idx_usage_metric", "usage(metric)"),
            ("idx_usage_reset_date", "usage(reset_date)")
        ]
        
        for index_name, table_column in indexes:
            sql = f"CREATE INDEX {index_name} ON {table_column};"
            self.execute_sql(sql, f"Created index {index_name}")
        
        # Create unique indexes
        unique_indexes = [
            ("ux_tenants_primary_domain", "tenants(primary_domain) WHERE primary_domain IS NOT NULL"),
            ("ux_users_provider_subject", "users(auth_provider, external_subject) WHERE external_subject IS NOT NULL"),
            ("ux_sections_tenant_name", "sections(tenant_id, section_name)"),
            ("ux_tsm_testcase_section", "testcase_section_map(testcase_id, section_id)"),
            ("ux_tcm_tc_map_testcase_tool", "tcm_testcase_mappings(testcase_id, tcm_tool)")
        ]
        
        for index_name, table_column in unique_indexes:
            sql = f"CREATE UNIQUE INDEX {index_name} ON {table_column};"
            self.execute_sql(sql, f"Created unique index {index_name}")

    def create_views(self):
        """Create convenience views for simpler queries."""
        logger.info("🪟 Creating views...")

        # Simple/latest requirement -> sections view via testcases linkage
        req_sections_view = """
        CREATE OR REPLACE VIEW requirement_sections_v AS
        SELECT DISTINCT rtm.requirement_id, s.section_id, s.section_name
        FROM requirement_testcase_map rtm
        JOIN testcase_section_map tsm ON tsm.testcase_id = rtm.testcase_id
        JOIN sections s ON s.section_id = tsm.section_id;
        """
        self.execute_sql(req_sections_view, "Created view requirement_sections_v")
    
    def create_triggers(self):
        """Create triggers for updated_at"""
        logger.info("⏰ Creating triggers...")
        
        # Create trigger function
        trigger_function = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """
        self.execute_sql(trigger_function, "Created trigger function")
        
        # Create triggers
        tables = ['requirement_labels', 'requirements', 'testcases', 'tenants', 'users', 'tcm_integrations', 'tcm_credentials', 'traceability_matrix', 'plans', 'subscriptions', 'usage']
        for table in tables:
            sql = f"CREATE TRIGGER update_{table}_updated_at BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();"
            self.execute_sql(sql, f"Created trigger for {table}")

        # Trigger to cascade-remove section links for a testcase when its TCM mapping is deleted
        cascade_fn = """
        CREATE OR REPLACE FUNCTION cascade_delete_section_links_for_tcm()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Remove links only for sections that originated from the same TCM tool
            DELETE FROM testcase_section_map m
            USING sections s
            WHERE m.section_id = s.section_id
              AND m.testcase_id = OLD.testcase_id
              AND s.source = OLD.tcm_tool;
            RETURN NULL; -- AFTER DELETE trigger
        END;
        $$ LANGUAGE plpgsql;
        """
        self.execute_sql(cascade_fn, "Created cascade function for TCM mapping deletes")

        cascade_trigger = """
        DROP TRIGGER IF EXISTS trg_cascade_tcm_mapping_delete ON tcm_testcase_mappings;
        CREATE TRIGGER trg_cascade_tcm_mapping_delete
        AFTER DELETE ON tcm_testcase_mappings
        FOR EACH ROW
        EXECUTE FUNCTION cascade_delete_section_links_for_tcm();
        """
        self.execute_sql(cascade_trigger, "Created trigger for cascading TCM mapping deletes")
    
    def insert_default_data(self):
        """Insert default tenant"""
        logger.info("👤 Creating default tenant...")
        
        sql = """
        INSERT INTO tenants (tenant_id, tenant_name, tenant_type, tenant_state, primary_domain) 
        VALUES (
            '00000000-0000-0000-0000-000000000000',
            'Default Tenant',
            'ORGANIZATION',
            'ACTIVE',
            'default.testcase-platform.com'
        ) ON CONFLICT (tenant_id) DO NOTHING;
        """
        self.execute_sql(sql, "Created default tenant")
    
    def insert_default_plans(self):
        """Insert default subscription plans"""
        logger.info("💳 Creating default subscription plans...")
        
        sql = """
        INSERT INTO plans (name, description, price, duration, limits, is_active) VALUES
        ('Free', 'Default free plan with limited features', '0.00', 'monthly', '{"uploads": 5, "testcases": 50, "api_calls": 1000}', true),
        ('Pro', 'Professional plan with enhanced features', '99.00', 'monthly', '{"uploads": 500, "testcases": 5000, "api_calls": 100000}', true),
        ('Unlimited', 'Standalone unlimited plan', '0.00', 'lifetime', '{"uploads": -1, "testcases": -1, "api_calls": -1}', true)
        ON CONFLICT (name) DO NOTHING;
        """
        self.execute_sql(sql, "Created default subscription plans")
    
    def initialize_database(self):
        """Initialize complete database"""
        logger.info("🚀 Initializing database with versioning schema...")
        
        try:
            self.connect()
            # Ensure pgcrypto extension exists for gen_random_uuid()
            self.execute_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto;", "Enabled pgcrypto")
            self.drop_existing_tables()
            self.create_tenants_table()
            self.create_requirement_labels_table()
            self.create_requirements_table()
            self.create_testcases_table()
            self.create_sections_table()
            self.create_testcase_section_map_table()
            self.create_mapping_table()
            self.create_users_table()
            self.create_tcm_integrations_table()
            self.create_tcm_credentials_table()
            self.create_tcm_testcase_mappings_table()
            self.create_testrail_projects_table()
            self.create_testrail_suites_table()
            self.create_zephyr_projects_table()
            self.create_xray_projects_table()
            self.create_traceability_matrix_table()
            self.create_plans_table()
            self.create_subscriptions_table()
            self.create_usage_table()
            self.create_indexes()
            self.create_triggers()
            self.create_views()
            self.insert_default_data()
            self.insert_default_plans()
            
            logger.info("✅ Database initialization completed successfully!")
            logger.info("📊 Tables created:")
            logger.info("  - tenants (IAM)")
            logger.info("  - users (IAM)")
            logger.info("  - requirement_labels")
            logger.info("  - requirements (with versioning)")
            logger.info("  - testcases (with versioning)")
            logger.info("  - requirement_testcase_map")
            logger.info("  - tcm_integrations")
            logger.info("  - tcm_credentials")
            logger.info("  - testrail_projects")
            logger.info("  - testrail_suites")
            logger.info("  - zephyr_projects")
            logger.info("  - xray_projects")
            logger.info("  - traceability_matrix")
            logger.info("  - plans (Subscription Management)")
            logger.info("  - subscriptions (Subscription Management)")
            logger.info("  - usage (Subscription Management)")
            logger.info("")
            logger.info("🔍 You can now start the application with versioning and subscription support!")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

def main():
    """Main function"""
    initializer = DatabaseInitializer()
    initializer.initialize_database()

if __name__ == "__main__":
    main()
