export interface MessageMetrics {
  timeToFirstToken?: number;
  totalTime?: number;
}

export interface Message {
  message_id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  created_at?: Date;
  isThinking?: boolean;
  model?: string;
  sources?: any[] | null;
  metrics?: MessageMetrics | null;
  rating?: 'up' | 'down' | null;
  session_id?: string;
  trace_id?: string;
  tool_calls?: any[] | null;
  tool_responses?: string[] | null;
}

export interface Chat {
  sessionId: string;
  firstQuery: string;
  messages: Message[];    
  timestamp: Date;
  isActive?: boolean;
} 