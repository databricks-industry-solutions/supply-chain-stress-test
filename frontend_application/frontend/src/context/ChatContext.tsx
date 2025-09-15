import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { sendMessage as apiSendMessage, getChatHistory, logout as apiLogout, deleteSession as apiDeleteSession, deleteAllSessions as apiDeleteAllSessions } from '../api/chatApi';
import { config } from '../config';
import { Message, Chat } from '../types';
import { v4 as uuid } from 'uuid';

interface ChatContextType {
  currentChat: Chat | null;
  chats: Chat[];
  messages: Message[];
  loading: boolean;
  sendMessage: (content: string, includeHistory: boolean) => Promise<void>;
  selectChat: (chatId: string) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  startNewSession: () => void;
  copyMessage: (content: string) => void;
  logout: () => void;
  deleteSession: (sessionId: string) => Promise<void>;
  deleteAllSessions: () => Promise<void>;
  error: string | null;
  clearError: () => void;
  currentEndpoint: string;
  setCurrentEndpoint: (endpointName: string) => void;
  currentSessionId: string | null;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: React.ReactNode }) => {
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [currentEndpoint, setCurrentEndpoint] = useState<string>(() => {
    // Initialize from localStorage if available, else empty string (will be loaded from config)
    const savedEndpoint = localStorage.getItem('selectedEndpoint');
    return savedEndpoint || '';
  });
  const [chats, setChats] = useState<Chat[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => {
    // Always start with a valid session ID
    return uuid();
  });
  const [error, setError] = useState<string | null>(null);
  const chatsLoadedRef = useRef(false);

  const clearError = () => setError(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        // Fetch config to get default endpoint if none is set
        if (!currentEndpoint) {
          const configResponse = await fetch(`${config.API_BASE_URL}/config`);
          if (configResponse.ok) {
            const configData = await configResponse.json();
            if (configData.serving_endpoint_name) {
              setCurrentEndpoint(configData.serving_endpoint_name);
            }
          }
        }

        // Fetch chat history
        const chatHistory = await getChatHistory();
        setChats(chatHistory.sessions || []);
      } catch (error) {
        console.error('Failed to fetch initial data:', error);
        setError('Failed to load initial data. Please try again.');
      }
    };

    fetchInitialData();
  }, []); // Don't include currentEndpoint in dependencies to avoid infinite loops


  // Open the sidebar if there are chats, but only once
  useEffect(() => {
    if(chats.length > 0 && chatsLoadedRef.current === false) {
      chatsLoadedRef.current = true;
      setIsSidebarOpen(true)
    }
  }, [chats]);

  const sendMessage = async (content: string, includeHistory: boolean = true) => {
    if (!content.trim()) return;

    // Create new session if needed and ensure we have a valid session ID
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = uuid();
      setCurrentSessionId(sessionId);
      setCurrentChat(null);
      setMessages([]);
    }

    const userMessage: Message = { 
      message_id: uuid(),
      content, 
      role: 'user',
      timestamp: new Date()
    };

    const thinkingMessage: Message = {
      message_id: uuid(),
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      isThinking: true
    };

    setMessages(prev => [...prev, userMessage, thinkingMessage]);
    setLoading(true);
    setError(null);

    try {
      let accumulatedContent = '';
      let messageSources: any[] | null = null;
      let messageMetrics: { timeToFirstToken?: number; totalTime?: number } | null = null;
      let messageId = '';
      let messageTraceId: string | null = null;
      let messageToolCalls: any[] | null = null;
      let messageToolResponses: string[] | null = null;
      let toolMessageCreated = false;
      
      await apiSendMessage(content, sessionId, includeHistory, currentEndpoint, (chunk) => {
        if (chunk.content) {
          accumulatedContent = chunk.content;
        }
        if (chunk.sources) {
          messageSources = chunk.sources;
        }
        if (chunk.metrics) {
          messageMetrics = chunk.metrics;
        }
        if (chunk.message_id) {
          messageId = chunk.message_id;
        }
        if (chunk.trace_id) {
          messageTraceId = chunk.trace_id;
        }
        // Accumulate tool calls and responses (don't overwrite with empty arrays)
        if (chunk.tool_calls && chunk.tool_calls.length > 0) {
          messageToolCalls = chunk.tool_calls;
        }
        if (chunk.tool_responses && chunk.tool_responses.length > 0) {
          messageToolResponses = chunk.tool_responses;
        }
    
        setMessages(prev => prev.map(msg => 
          msg.message_id === thinkingMessage.message_id 
            ? { 
                ...msg, 
                content: chunk.content || msg.content || '',
                sources: chunk.sources || msg.sources,
                metrics: chunk.metrics || msg.metrics,
                trace_id: chunk.trace_id || msg.trace_id,
                // Only update tool calls/responses if we have new non-empty data
                tool_calls: (chunk.tool_calls && chunk.tool_calls.length > 0) ? chunk.tool_calls : msg.tool_calls,
                tool_responses: (chunk.tool_responses && chunk.tool_responses.length > 0) ? chunk.tool_responses : msg.tool_responses,
                isThinking: false,
                model: currentEndpoint
              }
            : msg
        ));
      });
      
      // Don't create a final message - the streaming updates are sufficient
      // The message is already finalized through the streaming updates
      
    } catch (error) {
      console.error('Error sending message:', error);
      setError('Failed to send message. Please try again.');
      
      // Create error message with proper message_id
      const errorMessageId = uuid();
      const errorMessage: Message = { 
        message_id: errorMessageId,
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
        isThinking: false,
        model: currentEndpoint
      };
      
      // Keep the user message but update the thinking message to show error
      setMessages(prev => prev.map(msg => 
        msg.message_id === thinkingMessage.message_id 
          ? errorMessage
          : msg
      ));
    } finally {
      try {
        // Refresh chat history to pick up any new messages (like tool messages)
        const historyResponse = await fetch(`${config.API_BASE_URL}/chats`);
        const historyData = await historyResponse.json();
        if (historyData.sessions) {
          setChats(historyData.sessions);
          
          // Update current session messages to include any new tool messages
          if (sessionId) {
            const currentSession = historyData.sessions.find((session: any) => session.sessionId === sessionId);
            if (currentSession) {
              setMessages(currentSession.messages || []);
            }
          }
        }
      } catch (error) {
        console.error('Error fetching chat history:', error);
        setError('Failed to update chat history.');
      }
      setLoading(false);
    }
  };

  const selectChat = (sessionId: string) => {
    const selected = chats.find(chat => chat.sessionId === sessionId);
    
    if (selected) {
      setCurrentChat(selected);
      setCurrentSessionId(sessionId);
      
      const sessionMessages = chats
        .filter(chat => chat.sessionId === selected.sessionId)
        .flatMap(chat => chat.messages);
      
      setMessages(sessionMessages);
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const startNewSession = () => {
    const newSessionId = uuid();
    setCurrentSessionId(newSessionId);
    setCurrentChat(null);
    setMessages([]);
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
      .then(() => {
      })
      .catch(err => {
        console.error('Failed to copy message:', err);
        setError('Failed to copy message to clipboard.');
      });
  };

  const logout = () => {
    // Clear local state
    setCurrentChat(null);
    setChats([]);
    setMessages([]);
    setCurrentSessionId(null);
    
    // Call the logout API endpoint which will handle the redirect
    apiLogout();
  };

  const handleSetCurrentEndpoint = (endpointName: string) => {
    setCurrentEndpoint(endpointName);
    localStorage.setItem('selectedEndpoint', endpointName);
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await apiDeleteSession(sessionId);
      
      // Remove the deleted session from chats
      setChats(prev => prev.filter(chat => chat.sessionId !== sessionId));
      
      // If the deleted session was the current chat, start a new session
      if (currentChat?.sessionId === sessionId) {
        setCurrentChat(null);
        setMessages([]);
        startNewSession(); // Create a new session instead of setting to null
      }
      
      // Refresh chat history
      const chatHistory = await getChatHistory();
      setChats(chatHistory.sessions || []);
    } catch (error) {
      console.error('Failed to delete session:', error);
      setError('Failed to delete session. Please try again.');
    }
  };

  const deleteAllSessions = async () => {
    try {
      await apiDeleteAllSessions();
      
      // Clear all chats and current chat, but start a new session for future messages
      setChats([]);
      setCurrentChat(null);
      setMessages([]);
      startNewSession(); // Create a new session instead of setting to null
      
      // Refresh chat history
      const chatHistory = await getChatHistory();
      setChats(chatHistory.sessions || []);
    } catch (error) {
      console.error('Failed to delete all sessions:', error);
      setError('Failed to delete all sessions. Please try again.');
    }
  };

  return (
    <ChatContext.Provider value={{
      currentChat,
      chats,
      messages,
      loading,
      sendMessage,
      selectChat,
      isSidebarOpen,
      toggleSidebar,
      startNewSession,
      copyMessage,
      logout,
      deleteSession,
      deleteAllSessions,
      error,
      clearError,
      currentEndpoint,
      setCurrentEndpoint: handleSetCurrentEndpoint,
      currentSessionId
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}; 