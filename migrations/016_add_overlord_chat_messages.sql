-- Add table for Overlord chat messages
-- Migration: 016_add_overlord_chat_messages.sql

-- +migrate Up
CREATE TABLE overlord_chat_messages (
    pk UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    sender_pk UUID REFERENCES users(pk) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_overlord BOOLEAN NOT NULL DEFAULT FALSE,
    response_to UUID REFERENCES overlord_chat_messages(pk) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_overlord_chat_messages_conversation_id ON overlord_chat_messages(conversation_id);
CREATE INDEX idx_overlord_chat_messages_sender_pk ON overlord_chat_messages(sender_pk);
CREATE INDEX idx_overlord_chat_messages_created_at ON overlord_chat_messages(created_at);
CREATE INDEX idx_overlord_chat_messages_is_overlord ON overlord_chat_messages(is_overlord);

-- +migrate Down
DROP TABLE IF EXISTS overlord_chat_messages;
