export interface DocumentCollection {
  id: string;
  name: string;
  description?: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  tags: string[];
}

export interface DocumentCollectionCreate {
  name: string;
  description?: string;
  tags?: string[];
}

export interface DocumentCollectionUpdate {
  name?: string;
  description?: string;
  tags?: string[];
}

export interface DocumentCollectionResponse {
  success: boolean;
  message?: string;
  collection?: DocumentCollection;
}

export interface DocumentCollectionListResponse {
  success: boolean;
  message?: string;
  collections: DocumentCollection[];
} 