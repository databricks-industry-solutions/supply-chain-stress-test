import React, { useRef, useEffect, useState } from 'react';
import styled from 'styled-components';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { useChat } from '../context/ChatContext';
import ChatTopNav from './ChatTopNav';
import multiTierNetworkImage from '../assets/images/multi-tier-network.png';

interface ChatContainerProps {
  'data-testid'?: string;
  sidebarOpen: boolean;
}

const ChatContainer = styled.div<ChatContainerProps>`
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100vh;
  margin-left: ${props => props.sidebarOpen ? '300px' : '100px'};
  width: ${props => props.sidebarOpen ? 'calc(100% - 300px)' : 'calc(100% - 100px)'};
  transition: margin-left 0.3s ease, width 0.3s ease;
  overflow: hidden;
`;

const ChatContent = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  padding: 0 16px;
  overflow-y: auto;
  height: calc(100vh - 48px); 
`;

const WelcomeContainer = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'flex' : 'none'};
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 50%;
  min-width: 300px;
  margin: auto;
  margin-bottom: 150px;
  padding: 24px 16px;
`;

const WelcomeMessage = styled.h1`
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 24px;
  text-align: center;
`;

const ExampleQuestionsContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
  width: 100%;
  max-width: 600px;
`;

const ExampleQuestionsTitle = styled.h3`
  font-size: 16px;
  font-weight: 500;
  color: #666;
  margin-bottom: 16px;
  text-align: center;
`;

const ExampleQuestion = styled.button`
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 12px 16px;
  text-align: left;
  cursor: pointer;
  font-size: 14px;
  color: #495057;
  transition: all 0.2s ease;
  
  &:hover {
    background: #e9ecef;
    border-color: #dee2e6;
    transform: translateY(-1px);
  }
  
  &:active {
    transform: translateY(0);
  }
`;

const NetworkImageContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
  width: 100%;
`;

const NetworkImage = styled.img`
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 300px;
  object-fit: contain;
`;

const NetworkDescription = styled.p`
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 24px;
  line-height: 1.5;
  max-width: 600px;
`;

const FixedInputWrapper = styled.div<{ visible: boolean }>`
  display: ${props => props.visible ? 'flex' : 'none'};
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 660px;
  margin: 2px auto;
  position: sticky;
  bottom: 20px;
  background-color: white;
  z-index: 10;
  box-shadow: 0 -10px 20px rgba(255, 255, 255, 0.9);
`;

const MessagesContainer = styled.div`
  display: flex;
  flex-direction: column;
  width: 650px;
  margin: 0 auto;
  max-width: 100%;
`;

const ChatArea: React.FC = () => {
  const { messages, isSidebarOpen, sendMessage } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [hasStartedChat, setHasStartedChat] = useState(false);
  const [includeHistory, setIncludeHistory] = useState(true);

  useEffect(() => {
    if (messages?.length > 0 && !hasStartedChat) {
      setHasStartedChat(true);
    } else if (messages?.length === 0 && hasStartedChat) {
      // Reset hasStartedChat when messages is cleared (new session)
      setHasStartedChat(false);
    }
  }, [messages, hasStartedChat]);
  
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages]);
  
  const hasMessages = messages?.length > 0 || hasStartedChat;
  
  const exampleQuestions = [
    "List all downstream sites for the raw material supplied by T3_10, and include any related information about these sites.",
    "Tell me what happens if T2_8 is disrupted and requires 9 to recover. What should I do?",
    "What happens if T2_4 goes down and takes 6 weeks to recover? What should I do?",
    "There has been an incident at T3_15 and it will go down for the next 10 time units. Tell me what to do."
  ];
  
  const handleExampleQuestionClick = async (question: string) => {
    await sendMessage(question, true);
  };
  
  return (
    <ChatContainer data-testid="chat-area" sidebarOpen={isSidebarOpen}>
      <ChatTopNav />
      <ChatContent data-testid="chat-content">
        <WelcomeContainer visible={!hasMessages} data-testid="welcome-container">
          <WelcomeMessage data-testid="welcome-message">Supply Chain Stress Testing Assistant</WelcomeMessage>
          
          <NetworkImageContainer>
            <NetworkImage 
              src={multiTierNetworkImage} 
              alt="Multi-Tier Supply Chain Network"
              data-testid="network-image"
            />
          </NetworkImageContainer>
          
          <NetworkDescription>
            This assistant helps you analyze and stress test your multi-tier supply chain network. 
            The example questions below are based on the network structure shown above, which includes 
            Tier 1 products, Tier 2 suppliers, and Tier 3 sub-suppliers.
          </NetworkDescription>
          
          <ExampleQuestionsContainer>
            <ExampleQuestionsTitle>Try asking about the network:</ExampleQuestionsTitle>
            {exampleQuestions.map((question, index) => (
              <ExampleQuestion
                key={index}
                onClick={() => handleExampleQuestionClick(question)}
                data-testid={`example-question-${index}`}
              >
                {question}
              </ExampleQuestion>
            ))}
          </ExampleQuestionsContainer>
          
          <ChatInput 
            includeHistory={includeHistory}
            setIncludeHistory={setIncludeHistory}
            data-testid="chat-input" 
          />
        </WelcomeContainer>
        
        {hasMessages && (
          <MessagesContainer data-testid="messages-container" id="messages-container">
            {messages.map((message, index) => (
              <ChatMessage    
                key={index} 
                message={message}
                data-testid={`message-${index}`}
              />
            ))}
            {<div ref={messagesEndRef} />}
          </MessagesContainer>
        )}
      </ChatContent>
      
      <FixedInputWrapper visible={hasMessages} data-testid="fixed-input-wrapper">
        <ChatInput 
          fixed={true} 
          includeHistory={includeHistory}
          setIncludeHistory={setIncludeHistory}
        />
      </FixedInputWrapper>
    </ChatContainer>
  );
};

export default ChatArea; 