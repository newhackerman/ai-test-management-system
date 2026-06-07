/**
 * 对话管理器主组件
 */
import React, { useState } from 'react';
import { ConversationList } from './ConversationList';
import { CreateConversationDialog } from './CreateConversationDialog';
import { ConversationResponse } from '../../services/conversation-service';

interface ConversationManagerProps {
  onSelectConversation?: (conversation: ConversationResponse) => void;
  selectedConversationId?: number | null;
  className?: string;
}

export function ConversationManager({
  onSelectConversation,
  selectedConversationId,
  className = ''
}: ConversationManagerProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const handleCreateConversation = () => {
    setShowCreateDialog(true);
  };

  const handleConversationCreated = (conversation: ConversationResponse) => {
    // 自动选择新创建的对话
    onSelectConversation?.(conversation);
  };

  return (
    <div className={className}>
      <ConversationList
        onSelectConversation={onSelectConversation || (() => {})}
        onCreateConversation={handleCreateConversation}
        selectedConversationId={selectedConversationId}
      />

      <CreateConversationDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={handleConversationCreated}
      />
    </div>
  );
}