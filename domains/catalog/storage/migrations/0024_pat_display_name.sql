-- Add display_name to user_api_tokens for anonymous/alias commenting
ALTER TABLE user_api_tokens ADD COLUMN display_name TEXT;
