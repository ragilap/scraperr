export interface RowPrice {
    row: string;
    price: number;
}

export interface Section {
    currency: string;
    rows: RowPrice[];
}

export interface EventDetails {
    url: string;
    title: string;
    held_on: string;
    location: string;
    sections: {
        [key: string]: Section;
    };
    recommendations: string[];
    count: {
        section: number;
        row: number;
    };
}