import React, { useState } from 'react';
import styled from 'styled-components';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes, faThumbsUp, faThumbsDown } from '@fortawesome/free-solid-svg-icons';

const PopupOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const PopupContainer = styled.div`
  background: white;
  border-radius: 12px;
  padding: 24px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  position: relative;
`;

const CloseButton = styled.button`
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #666;
  
  &:hover {
    color: #333;
  }
`;

const Title = styled.h3`
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
`;

const RatingSection = styled.div`
  margin-bottom: 20px;
`;

const RatingLabel = styled.label`
  display: block;
  margin-bottom: 12px;
  color: #555;
  font-weight: 500;
`;

const RatingButtons = styled.div`
  display: flex;
  gap: 12px;
`;

const RatingButton = styled.button<{ isSelected: boolean; isPositive: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border: 2px solid ${props => props.isSelected ? (props.isPositive ? '#4CAF50' : '#F44336') : '#E0E0E0'};
  border-radius: 8px;
  background: ${props => props.isSelected ? (props.isPositive ? '#E8F5E8' : '#FFEBEE') : 'white'};
  color: ${props => props.isSelected ? (props.isPositive ? '#2E7D32' : '#C62828') : '#666'};
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: ${props => props.isPositive ? '#4CAF50' : '#F44336'};
    background: ${props => props.isPositive ? '#F1F8E9' : '#FFCDD2'};
  }
`;

const CommentSection = styled.div`
  margin-bottom: 24px;
`;

const CommentLabel = styled.label`
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
`;

const CommentTextarea = styled.textarea`
  width: 100%;
  min-height: 100px;
  padding: 12px;
  border: 2px solid #E0E0E0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  
  &:focus {
    outline: none;
    border-color: #2272B4;
  }
`;

const SubmitButton = styled.button`
  background: #2272B4;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  width: 100%;
  
  &:hover {
    background: #1B5F8A;
  }
  
  &:disabled {
    background: #BDBDBD;
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.div`
  color: #F44336;
  font-size: 14px;
  margin-top: 12px;
  text-align: center;
`;

const SuccessMessage = styled.div`
  color: #4CAF50;
  font-size: 14px;
  margin-top: 12px;
  text-align: center;
`;

interface FeedbackPopupProps {
  isOpen: boolean;
  onClose: () => void;
  messageId: string;
  sessionId: string;
  onSubmit: (feedback: { rating: 'up' | 'down'; comment?: string }) => Promise<{ success: boolean; message?: string }>;
}

const FeedbackPopup: React.FC<FeedbackPopupProps> = ({
  isOpen,
  onClose,
  messageId,
  sessionId,
  onSubmit
}) => {
  const [rating, setRating] = useState<'up' | 'down' | null>(null);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!rating) {
      setError('Please select a rating');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const result = await onSubmit({ rating, comment: comment.trim() || undefined });
      
      if (result && result.success) {
        setSuccess(true);
        setTimeout(() => {
          onClose();
          setSuccess(false);
          setRating(null);
          setComment('');
        }, 1500);
      } else {
        setError(result?.message || 'Failed to submit feedback. Please try again.');
      }
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      onClose();
      setRating(null);
      setComment('');
      setError('');
      setSuccess(false);
    }
  };

  if (!isOpen) return null;

  return (
    <PopupOverlay onClick={handleClose}>
      <PopupContainer onClick={(e) => e.stopPropagation()}>
        <CloseButton onClick={handleClose}>
          <FontAwesomeIcon icon={faTimes} />
        </CloseButton>
        
        <Title>Provide Feedback</Title>
        
        <RatingSection>
          <RatingLabel>How would you rate this response?</RatingLabel>
          <RatingButtons>
            <RatingButton
              isSelected={rating === 'up'}
              isPositive={true}
              onClick={() => setRating('up')}
            >
              <FontAwesomeIcon icon={faThumbsUp} />
              Thumbs Up
            </RatingButton>
            <RatingButton
              isSelected={rating === 'down'}
              isPositive={false}
              onClick={() => setRating('down')}
            >
              <FontAwesomeIcon icon={faThumbsDown} />
              Thumbs Down
            </RatingButton>
          </RatingButtons>
        </RatingSection>
        
        <CommentSection>
          <CommentLabel>Additional comments (optional)</CommentLabel>
          <CommentTextarea
            placeholder="Tell us more about your experience with this response..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={500}
          />
        </CommentSection>
        
        <SubmitButton
          onClick={handleSubmit}
          disabled={!rating || isSubmitting}
        >
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </SubmitButton>
        
        {error && <ErrorMessage>{error}</ErrorMessage>}
        {success && <SuccessMessage>Feedback submitted successfully!</SuccessMessage>}
      </PopupContainer>
    </PopupOverlay>
  );
};

export default FeedbackPopup; 