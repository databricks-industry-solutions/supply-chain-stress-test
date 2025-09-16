import React, { useState } from 'react';
import styled from 'styled-components';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronDown, faChevronRight } from '@fortawesome/free-solid-svg-icons';

const ToolCallContainer = styled.div`
  margin: 16px 0;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  background-color: #f8f9fa;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
`;

const ToolCallHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background-color: #e9ecef;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: #dee2e6;
  }
`;

const ToolCallTitle = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #495057;
  font-size: 14px;
`;

const ToolIcon = styled.div`
  width: 20px;
  height: 20px;
  background-color: #007bff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: bold;
`;


const ChevronIcon = styled(FontAwesomeIcon)<{ isExpanded: boolean }>`
  transition: transform 0.2s ease;
  transform: ${props => props.isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'};
  color: #6c757d;
`;

const ToolCallContent = styled.div<{ isExpanded: boolean }>`
  max-height: ${props => props.isExpanded ? '1000px' : '0'};
  overflow: hidden;
  transition: max-height 0.3s ease;
`;

const JsonContainer = styled.div`
  padding: 16px;
  background-color: #ffffff;
  border-top: 1px solid #e1e5e9;
`;

const JsonPre = styled.pre`
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #2d3748;
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #f7fafc;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  overflow-x: auto;
`;

interface ToolCallDisplayProps {
  toolCalls: any[];
}

const ToolCallDisplay: React.FC<ToolCallDisplayProps> = ({ toolCalls }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const formatJson = (obj: any): string => {
    return JSON.stringify(obj, null, 2);
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <ToolCallContainer>
              <ToolCallHeader onClick={toggleExpanded}>
          <ToolCallTitle>
            <ToolIcon>T</ToolIcon>
            Tool Calls ({toolCalls.length})
          </ToolCallTitle>
        <ChevronIcon 
          icon={isExpanded ? faChevronDown : faChevronRight} 
          isExpanded={isExpanded}
        />
      </ToolCallHeader>
      <ToolCallContent isExpanded={isExpanded}>
        <JsonContainer>
          <JsonPre>{formatJson(toolCalls)}</JsonPre>
        </JsonContainer>
      </ToolCallContent>
    </ToolCallContainer>
  );
};

export default ToolCallDisplay;
