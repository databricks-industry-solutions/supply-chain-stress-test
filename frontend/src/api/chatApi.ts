import { Chat } from '../types';
import { config } from '../config';

// API Configuration
const API_URL = config.API_BASE_URL;


export const sendMessage = async (
  content: string, 
  sessionId: string,
  includeHistory: boolean,
  servingEndpointName: string,
  onChunk: (chunk: { 
    message_id: string,
    content?: string, 
    sources?: any[],
    metrics?: {
      timeToFirstToken?: number;
      totalTime?: number;
    },
    model?: string,
    trace_id?: string,  // Add trace_id to chunk type
    tool_calls?: any[],  // Add tool_calls to chunk type
    tool_responses?: string[]  // Add tool_responses to chunk type
  }) => void,
): Promise<void> => {
  try {
    const response = await fetch(
      `${API_URL}/chat`, 
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ 
          content,
          session_id: sessionId,
          include_history: includeHistory,
          serving_endpoint_name: servingEndpointName
        })
      }
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No reader available');
    }

    const decoder = new TextDecoder();
    let accumulatedContent = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.slice(6);
          if (jsonStr && jsonStr !== '{}') {
            try {
              const data = JSON.parse(jsonStr);
              // Double parse if the first parse returned a string
              const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
              
              // Use the accumulated content directly from the backend
              // The backend now sends the full accumulated content with each chunk
              onChunk({
                message_id: parsedData.message_id,
                content: parsedData.content || accumulatedContent, // Use backend's accumulated content
                sources: parsedData.sources,
                metrics: parsedData.metrics,
                trace_id: parsedData.trace_id, // Add trace_id to onChunk callback
                tool_calls: parsedData.tool_calls, // Add tool_calls to onChunk callback
                tool_responses: parsedData.tool_responses // Add tool_responses to onChunk callback
              });
            } catch (e) {
              console.error('Error parsing JSON:', e);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

export const getChatHistory = async (): Promise<{ sessions: Chat[] }> => {
  try {
    const response = await fetch(`${API_URL}/chats`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching chat history:', error);
    return { sessions: [] };
  }
};

export const fetchUserInfo = async (): Promise<{ username: string; email: string, displayName: string }> => {
  try {
    const response = await fetch(`${API_URL}/user-info`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching user info:', error);
    throw error;
  }
};


export const logout = async () => {
  window.location.href = `${API_URL}/logout`;
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  try {
    const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
  } catch (error) {
    console.error('Error deleting session:', error);
    throw error;
  }
};

export const deleteAllSessions = async (): Promise<void> => {
  try {
    const response = await fetch(`${API_URL}/sessions`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
  } catch (error) {
    console.error('Error deleting all sessions:', error);
    throw error;
  }
};

export interface ServingEndpoint {
  name: string;
  state: string;
}

export const rateMessage = async (
  messageId: string,
  sessionId: string,
  rating: 'up' | 'down'
): Promise<void> => {
  try {
    const response = await fetch(`${API_URL}/rate-message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message_id: messageId,
        session_id: sessionId,
        rating: rating
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
  } catch (error) {
    console.error('Error rating message:', error);
    throw error;
  }
};

export const removeRating = async (
  messageId: string,
  sessionId: string
): Promise<void> => {
  try {
    const response = await fetch(`${API_URL}/rate-message`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message_id: messageId,
        session_id: sessionId
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
  } catch (error) {
    console.error('Error removing rating:', error);
    throw error;
  }
};

export interface FeedbackData {
  message_id: string;
  session_id: string;
  rating: 'up' | 'down';
  comment?: string;
  trace_id?: string;
}

export const submitFeedback = async (feedback: FeedbackData): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await fetch(`${API_URL}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(feedback)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error submitting feedback:', error);
    throw error;
  }
};
