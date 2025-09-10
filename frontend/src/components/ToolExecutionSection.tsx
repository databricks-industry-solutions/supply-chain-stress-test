import React, { useState } from 'react';
import styled from 'styled-components';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChevronDown } from '@fortawesome/free-solid-svg-icons';

const ToolExecutionContainer = styled.div`
  margin: 20px 0;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 0;
  border: 1px solid #e9ecef;
  overflow: hidden;
`;

const ToolExecutionHeader = styled.div`
  background: linear-gradient(135deg, #7c7c7c 0%, #8e8e8e 100%);
  color: white;
  padding: 8px 12px;
  font-weight: 500;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 0;
  margin-bottom: 0;
  border-bottom: 1px solid #e9ecef;
`;

const ToolCallCell = styled.div`
  margin-bottom: 0;
  border: none;
  border-bottom: 1px solid #e9ecef;
  border-radius: 0;
  background: white;
  overflow: hidden;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: #f8f9fa;
  }
  
  &:last-child {
    border-bottom: none;
  }
`;

const ToolCallHeader = styled.div`
  background: transparent;
  padding: 12px 16px;
  border-bottom: ${props => props.theme?.isExpanded ? '1px solid #e9ecef' : 'none'};
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
  color: #6c757d;
  transition: all 0.2s ease;

  &:hover {
    background-color: #f8f9fa;
    color: #495057;
  }
`;

const ToolCallTitle = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 400;
`;

const CollapseIcon = styled.div<{ isOpen: boolean }>`
  transform: ${props => props.isOpen ? 'rotate(180deg)' : 'rotate(0deg)'};
  transition: all 0.2s ease;
  font-size: 12px;
  color: #adb5bd;
  font-weight: normal;
`;

const ToolCallContent = styled.div<{ isOpen: boolean }>`
  max-height: ${props => props.isOpen ? '1000px' : '0'};
  overflow: hidden;
  transition: max-height 0.3s ease;
`;

const ToolCallBody = styled.div`
  padding: 16px;
  background: #fafafa;
`;

const ToolCallArgs = styled.div`
  margin-bottom: 20px;
`;

const ToolCallArgsLabel = styled.div`
  font-weight: 500;
  color: #495057;
  margin-bottom: 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '📋';
    font-size: 12px;
  }
`;

const ToolResponse = styled.div`
  margin-top: 0;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 0;
  border-left: 3px solid #6c757d;
`;

const ToolResponseLabel = styled.div`
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 8px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '📤';
    font-size: 12px;
  }
`;

const JsonContainer = styled.div`
  background: white;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #e9ecef;
  overflow: auto;
  max-height: 300px;
`;

interface ToolExecutionSectionProps {
  toolCalls: any[];
  toolResponses: string[];
}

const ToolExecutionSection: React.FC<ToolExecutionSectionProps> = ({ toolCalls, toolResponses }) => {
  const [expandedCells, setExpandedCells] = useState<{ [key: string]: boolean }>({});

  // Debug logging
  console.log('ToolExecutionSection received:', { toolCalls, toolResponses });
  console.log('toolCalls type:', typeof toolCalls, 'length:', toolCalls?.length);

  if (!toolCalls || toolCalls.length === 0) {
    console.log('ToolExecutionSection returning null - no tool calls');
    return null;
  }
  
  console.log('ToolExecutionSection rendering with', toolCalls.length, 'tool calls');

  const formatJson = (jsonString: string) => {
    try {
      const parsed = JSON.parse(jsonString);
      return JSON.stringify(parsed, null, 2);
    } catch (e) {
      return jsonString;
    }
  };

  const toggleCell = (cellId: string) => {
    setExpandedCells(prev => ({
      ...prev,
      [cellId]: !prev[cellId]
    }));
  };

  // Just return null - don't render any separate tool execution UI
  // Tool information should be integrated into the main content flow
  return null;
};

export default ToolExecutionSection;
